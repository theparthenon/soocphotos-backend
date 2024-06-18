# pylint: disable=broad-except, protected-access
"""Utility functions for face recognition."""

import datetime
import uuid
import pytz

from django import db
from django_q.tasks import AsyncTask

from api.face_classify import cluster_all_faces
from api.models import Job, Photos
from api.utils import logger


def scan_faces(user, job_id):
    """Scans the faces of all photos owned by the given user and performs face
    recognition on them."""

    if Job.objects.filter(job_id=job_id).exists():
        lrj = Job.objects.get(job_id=job_id)
        lrj.started_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
    else:
        lrj = Job.objects.create(
            started_by=user,
            job_id=job_id,
            queued_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            started_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            job_type=Job.JOB_SCAN_FACES,
        )

    lrj.save()

    try:
        existing_photos = Photos.objects.filter(owner=user.id)
        all_photos = [(photo, job_id) for photo in existing_photos]

        lrj.result = {"progress": {"current": 0, "target": existing_photos.count()}}
        lrj.save()
        db.connections.close_all()

        for photo in all_photos:
            face_scanner(*photo)

    except Exception as e:
        logger.exception("An error occured: ")
        print(f"[ERR]: {format(e)}")
        lrj.failed = True

    cluster_job_id = uuid.uuid4()
    AsyncTask(cluster_all_faces, user, cluster_job_id).run()


def face_scan_job(photo: Photos, job_id):
    """Updates the progress and status of a face scan job in the database."""

    failed = False

    try:
        photo._extract_faces()
    except Exception:
        logger.exception("An error occurred: ")
        failed = True

    with db.connection.cursor() as cursor:
        cursor.execute(
            """
                update api_Job
                set result = jsonb_set(result,'{"progress","current"}',
                      ((jsonb_extract_path(result,'progress','current')::int + 1)::text)::jsonb
                ) where job_id = %(job_id)s""",
            {"job_id": str(job_id)},
        )
        cursor.execute(
            """
                update api_Job
                set finished = true
                where job_id = %(job_id)s and
                        (result->'progress'->>'current')::int = (result->'progress'->>'target')::int
            """,
            {"job_id": str(job_id)},
        )

        if failed:
            cursor.execute(
                """
                    update api_Job
                    set failed = %(failed)s
                    where job_id = %(job_id)s
                """,
                {"job_id": str(job_id), "failed": failed},
            )


def face_scanner(photo: Photos, job_id):
    """Runs the face_scanner task asynchronously using the AsyncTask class."""

    AsyncTask(face_scan_job, photo, job_id).run()
