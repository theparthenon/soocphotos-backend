# pylint: disable=protected-access
"""Directory functions."""

import datetime
import os
import stat
import uuid
from typing import List, Optional

import pytz
from constance import config as site_config
from django import db
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django_q.tasks import AsyncTask

from api.face_classify import cluster_all_faces
from api.models import Job, Photos
from api.models.file import File
from api.utils import (
    calculate_hash,
    get_sidecar_files_in_priority_order,
    is_metadata,
    is_video,
    logger,
    is_valid_media,
)


def should_skip(path):
    """Decides if the path should be skipped."""

    if not site_config.SKIP_PATTERNS:
        return False

    skip_patterns = site_config.SKIP_PATTERNS
    skip_list = skip_patterns.split(",")
    skip_list = map(str.strip, skip_list)

    res = [ele for ele in skip_list if ele in path]

    return bool(res)


if os.name == "Windows":

    def is_hidden(path):
        """On Windows systems, check if the path is hidden."""

        name = os.path.basename(os.path.abspath(path))
        return name.startswith(".") or has_hidden_attribute(path)

    def has_hidden_attribute(path):
        """On Windows systems, check if the path has hidden attribute."""

        try:
            return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
        except OSError:
            return False

else:

    def is_hidden(path):
        """On Unix systems, check if the path starts with a dot."""

        return os.path.basename(path).startswith(".")


def update_scan_counter(job_id):
    """Updates the scan counter for a given job."""

    with db.connection.cursor() as cursor:
        cursor.execute(
            """
                update api_Job
                set result = jsonb_set(result, '{"progress", "current"}',
                    ((jsonb_extract_path(result, 'progress', 'current')::int +1)::text)::jsonb
                ) where job_id = %(job_id)s""",
            {"job_id": str(job_id)},
        )
        cursor.execute(
            """
                update api_Job
                set finished = true, finished_at = now()
                where job_id = %(job_id)s and
                        (result->'progress'->>'total')::int = (result->'progress'->>'current')::int
            """,
            {"job_id": str(job_id)},
        )


def create_new_image(user, path) -> Optional[Photos]:
    """Creates a new image record in the database if the provided path is valid
    media and the image hash does not already exist in the database."""

    if not is_valid_media(path):
        return

    img_hash = calculate_hash(user, path)

    if is_metadata(path):
        photo_name = os.path.splitext(os.path.basename(path))[0]
        photo_dir = os.path.dirname(path)
        photo = Photos.objects.filter(
            Q(files__path__contains=photo_dir)
            & Q(files__path__contains=photo_name)
            & ~Q(files__path__contains=os.path.basename(path))
        ).first()

        if photo:
            file = File.create(path, user)
            photo.files.add(file)
            photo.save()

        else:
            logger.warning("No photo to metadata file found %s", path)

        return

    photos: QuerySet[Photos] = Photos.objects.filter(Q(image_hash=img_hash))

    if not photos.exists():
        photo: Photos = Photos()
        photo.image_hash = img_hash
        photo.owner = user
        photo.added_on = datetime.datetime.now().replace(tzinfo=pytz.UTC)
        photo.geolocation_json = {}
        photo.video = is_video(path)
        photo.save()
        file = File.create(path, user)
        photo.files.add(file)
        photo.original_image = file
        photo.save()

        return photo
    else:
        file = File.create(path, user)
        photo = photos.first()
        photo.files.add(file)
        photo.save()
        photo._check_files()
        logger.warning("Photo %s already exists.", path)

        return None


def handle_new_image(user, path, job_id, photo=None):
    """Handles the creation and all the processing of the photo."""

    update_scan_counter(job_id)
    try:
        start = datetime.datetime.now()
        if photo is None:
            photo = create_new_image(user, path)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info("Job %d: save image: %s, elapsed: %s", job_id, path, elapsed)
        if photo:
            logger.info("job %d: handling image %s", job_id, path)
            photo._generate_optimized_image(True)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: generate optimized image: %s, elapsed: %s",
                job_id,
                path,
                elapsed,
            )
            photo._generate_thumbnail(True)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: generate thumbnails: %s, elapsed: %s", job_id, path, elapsed
            )
            photo._generate_captions(False)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: generate caption: %s, elapsed: %s", job_id, path, elapsed
            )
            photo._geolocate(True)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info("job %d: geolocate: %s, elapsed: %s", job_id, path, elapsed)
            photo._extract_date_time_from_exif(True)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: extract date time: %s, elapsed: %s", job_id, path, elapsed
            )
            photo._extract_exif_data(True)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: extract exif data: %s, elapsed: %s", job_id, path, elapsed
            )
            photo._extract_faces()
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info("job %d: extract faces: %s, elapsed: %s", job_id, path, elapsed)
            photo._get_dominant_color()
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: get dominant color: %s, elapsed: %s", job_id, path, elapsed
            )
            photo._recreate_search_captions()
            elapsed = (datetime.datetime.now() - start).total_seconds()
            logger.info(
                "job %d: seach caption recreated: %s, elapsed: %s",
                job_id,
                path,
                elapsed,
            )

    except OSError as e:
        try:
            logger.exception(
                "job %d: could not load image %s. reason: %s", job_id, path, str(e)
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception("job %d: could not load image %s", job_id, path)


def rescan_image(user, path, job_id):  # pylint: disable=unused-argument
    """Rescans the given image based on path location."""

    update_scan_counter(job_id)

    try:
        if is_valid_media(path):
            photo = Photos.objects.filter(Q(files__path=path)).get()
            photo._generate_optimized_image(True)
            photo._generate_thumbnail(True)
            # photo._geolocate(True)
            # photo._extract_exif_data(True)
            # photo._extract_date_time_from_exif(True)
            photo._get_dominant_color()
            photo._recreate_search_captions()

    except OSError as e:
        try:
            logger.exception(
                "job %d: could not load image %s. reason: %s", job_id, path, e
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception("job %d: could not load image %s", job_id, path)


def walk_directory(directory, callback):
    """Opens any directories available in the given directory and directories inside them."""

    for file in os.scandir(directory):
        fpath = os.path.join(directory, file)

        if not is_hidden(fpath) and not should_skip(fpath):
            if os.path.isdir(fpath):
                walk_directory(fpath, callback)
            else:
                callback.append(fpath)


def walk_files(scan_files, callback):
    """Checks the given files and calls the callback function for each one."""

    for fpath in scan_files:
        if os.path.isfile(fpath):
            callback.append(fpath)


def _file_was_modified_after(filepath, time):
    """Determines if the file was modified after the given time."""

    try:
        modified = os.path.getmtime(filepath)
    except OSError as e:
        logger.error("could not get modified time for %s: %s", filepath, e)

        return False

    return datetime.datetime.fromtimestamp(modified).replace(tzinfo=pytz.utc) > time


def photo_scanner(user, last_scan, full_scan, path, job_id):
    """Scans the given path for new photos."""

    if Photos.objects.filter(files__path=path).exists():
        files_to_check = [path]
        files_to_check.extend(get_sidecar_files_in_priority_order(path))

        if (
            full_scan
            or not last_scan
            or any(
                [
                    _file_was_modified_after(p, last_scan.finished_at)
                    for p in files_to_check
                ]
            )
        ):
            AsyncTask(rescan_image, user, path, job_id).run()
        else:
            update_scan_counter(job_id)
    else:
        old_path = path
        photo_name = os.path.splitext(os.path.basename(path))[0]
        photo_ext = os.path.splitext(os.path.basename(path))[1]
        new_path = os.path.join(settings.PHOTOS, photo_name + photo_ext)
        os.rename(old_path, new_path)

        AsyncTask(handle_new_image, user, new_path, job_id).run()


def scan_directory(
    directory: Optional[str] = None,
    ignored_items: Optional[tuple] = None,
    wanted_extensions: Optional[tuple] = None,
) -> List[str]:
    """Scans the given directory and returns a list of all wanted files."""

    all_images = []

    directory = directory or "."

    ignored_items = ignored_items or (
        ".git",
        ".idea",
        "venv",
        "__pycache__",
    )

    wanted_extensions = wanted_extensions or (
        "jpg",
        "jpeg",
        "png",
        "gif",
        "heif",
        "heic",
        "bmp",
        "tiff",
        "webp",
        "mov",
        "mp4",
        "avi",
        "webm",
        "mkv",
        "m4v",
    )

    for root, dirs, files in os.walk(directory):  # pylint: disable=unused-variable
        if any(ignore_item in root for ignore_item in ignored_items):
            continue

        for file in files:
            if any(ignore_item in file for ignore_item in ignored_items):
                continue

            file_extension = os.path.splitext(file)[1].lower()[1:]

            if file_extension not in wanted_extensions:
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, "rb"):
                    all_images.append(file_path)
            except FileNotFoundError:
                logger.warning("File %s was not found", file_path)
            except PermissionError:
                logger.warning("Permission denied for file %s", file_path)

    return all_images


def scan_photos(
    user, full_scan, job_id, scan_dir="", scan_files=[]
):  # pylint: disable=dangerous-default-value, unused-argument
    """Scan photos in the given path and calls the callback function for each one."""

    print("Starting scan_photos")

    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, "optimized")):
        os.mkdir(os.path.join(settings.MEDIA_ROOT, "originals"))
        os.mkdir(os.path.join(settings.MEDIA_ROOT, "optimized"))
        os.mkdir(os.path.join(settings.MEDIA_ROOT, "thumbnails"))

    if Job.objects.filter(job_id=job_id).exists():
        lrj = Job.objects.get(job_id=job_id)
        lrj.started_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
    else:
        lrj = Job.objects.create(
            started_by=user,
            job_id=job_id,
            queued_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            started_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            job_type=1,
        )

    lrj.save()
    photo_count_before = Photos.objects.count()

    try:
        if scan_dir == "":
            scan_dir = user.scan_directory

        print("Scanning directory:", scan_dir)

        photo_list = scan_directory(directory=scan_dir)

        files_found = len(photo_list)
        print("Found", files_found, "files")

        last_scan = (
            Job.objects.filter(finished=True)
            .filter(job_type=1)
            .filter(started_by=user)
            .order_by("-finished_at")
            .first()
        )

        all_photos = []

        for path in photo_list:
            all_photos.append((user, last_scan, full_scan, path, job_id))

        lrj.result = {"progress": {"current": 0, "target": files_found}}
        lrj.save()
        db.connections.close_all()

        for photo in all_photos:
            photo_scanner(*photo)

        print("Scanned", files_found, "files in:", scan_directory)

        existing_photos = Photos.objects.filter(owner=user.id).order_by("image_hash")
        paginator = Paginator(existing_photos, 5000)

        for page in range(1, paginator.num_pages + 1):
            for existing_photo in paginator.page(page).object_list:
                existing_photo._check_files()

        print("Finished checking paths")
    except OSError as e:
        print("job", job_id, ": could not scan photos:", e)
        lrj.failed = True

    added_photo_count = Photos.objects.count() - photo_count_before
    print("Added", added_photo_count, "photos")

    cluster_job_id = uuid.uuid4()
    print("Starting cluster_all_faces")
    AsyncTask(cluster_all_faces, user, cluster_job_id).run()

    print("Finished scan_photos")
