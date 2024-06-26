import io
import os
import uuid
import zipfile
from datetime import datetime

import pytz
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django_q.tasks import AsyncTask, schedule

from api.models import (
    AlbumDate,
    AlbumPlace,
    AlbumThing,
    Albums,
    Face,
    File,
    Job,
    Photos,
)
from api.utils import logger


def create_download_job(job_type, user, photos, filename):
    job_id = uuid.uuid4()
    lrj = Job.objects.create(
        started_by=user,
        job_id=job_id,
        queued_at=datetime.now().replace(tzinfo=pytz.utc),
        job_type=job_type,
    )

    if job_type == Job.JOB_DOWNLOAD_PHOTOS:
        AsyncTask(
            zip_photos_task, job_id=job_id, user=user, photos=photos, filename=filename
        ).run()

    lrj.save()

    return job_id


def zip_photos_task(job_id, user, photos, filename):
    lrj = Job.objects.get(job_id=job_id)
    lrj.started_at = datetime.now().replace(tzinfo=pytz.utc)
    count = len(photos)
    lrj.result = {"progress": {"current": 0, "target": count}}
    lrj.save()
    output_directory = os.path.join(settings.MEDIA_ROOT, "zip")
    zip_file_name = filename
    done_count = 0

    try:
        if not os.path.exists(output_directory):
            os.mkdir(output_directory)
        mf = io.BytesIO()
        photos_name = {}

        for photo in photos:
            done_count = done_count + 1
            photo_name = os.path.basename(photo.main_file.path)

            if photo_name in photos_name:
                photos_name[photo_name] = photos_name[photo_name] + 1
                photo_name = str(photos_name[photo_name]) + "-" + photo_name
            else:
                photos_name[photo_name] = 1

            with zipfile.ZipFile(mf, mode="a", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(photo.main_file.path, arcname=photo_name)

            lrj.result = {"progress": {"current": done_count, "target": count}}
            lrj.save()

        with open(os.path.join(output_directory, zip_file_name), "wb") as output_file:
            output_file.write(mf.getvalue())

    except Exception as e:
        logger.error("Error while converting files to zip: %s", e)

    lrj.finished_at = datetime.now().replace(tzinfo=pytz.utc)
    lrj.finished = True
    lrj.save()
    # scheduling a task to delete the zip file after a day
    execution_time = timezone.now() + timezone.timedelta(days=1)
    schedule("api.all_tasks.delete_zip_file", filename, next_run=execution_time)

    return os.path.join(output_directory, zip_file_name)


def delete_missing_photos(user, job_id):
    if Job.objects.filter(job_id=job_id).exists():
        lrj = Job.objects.get(job_id=job_id)
        lrj.started_at = datetime.now().replace(tzinfo=pytz.utc)
        lrj.save()
    else:
        lrj = Job.objects.create(
            started_by=user,
            job_id=job_id,
            queued_at=datetime.now().replace(tzinfo=pytz.utc),
            started_at=datetime.now().replace(tzinfo=pytz.utc),
            job_type=Job.JOB_DELETE_MISSING_PHOTOS,
        )
        lrj.save()
    try:
        missing_photos = Photos.objects.filter(
            Q(owner=user) & Q(files=None) | Q(main_file=None)
        )
        for missing_photo in missing_photos:
            album_dates = AlbumDate.objects.filter(photos=missing_photo)
            for album_date in album_dates:
                album_date.photos.remove(missing_photo)
            album_things = AlbumThing.objects.filter(photos=missing_photo)
            for album_thing in album_things:
                album_thing.photos.remove(missing_photo)
            album_places = AlbumPlace.objects.filter(photos=missing_photo)
            for album_place in album_places:
                album_place.photos.remove(missing_photo)
            albums = Albums.objects.filter(photos=missing_photo)
            for album in albums:
                album.photos.remove(missing_photo)
            faces = Face.objects.filter(photo=missing_photo)
            faces.delete()
            # To-Do: Remove thumbnails

        missing_photos.delete()

        missing_files = File.objects.filter(Q(hash__endswith=user) & Q(missing=True))
        missing_files.delete()

        lrj.finished = True
        lrj.finished_at = datetime.now().replace(tzinfo=pytz.utc)
        lrj.save()
    except Exception:
        logger.exception("An error occurred")
        lrj.failed = True
        lrj.finished = True
        lrj.finished_at = datetime.now().replace(tzinfo=pytz.utc)
        lrj.save()

    return 1


def delete_zip_file(filename):
    file_path = os.path.join(settings.MEDIA_ROOT, "zip", filename)

    try:
        if not os.path.exists(file_path):
            logger.error("Error while deleting file not found at : %s", file_path)

            return
        else:
            os.remove(file_path)
            logger.info("file deleted sucessfully at path : %s", file_path)

            return

    except Exception as e:
        logger.error("Error while deleting file: %s", e)

        return e
