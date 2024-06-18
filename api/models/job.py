"""Create Photos model for database."""

from datetime import datetime

from django.db import models
import pytz

from api.models.user import get_deleted_user, User


def get_default_job_result():
    """Returns a dictionary with a default job result, containing the progress of a job."""

    return {"progress": {"target": 0, "current": 0}}


class Job(models.Model):
    """Initialize Job model."""

    JOB_SCAN_PHOTOS = 1
    JOB_SCAN_FACES = 2
    JOB_TRAIN_FACES = 3
    JOB_CLUSTER_ALL_FACES = 4
    JOB_DELETE_MISSING_PHOTOS = 5
    JOB_DOWNLOAD_PHOtoS = 6
    JOB_DOWLOAD_MODELS = 7

    JOB_TYPES = (
        (JOB_SCAN_PHOTOS, "Scan Photos"),
        (JOB_SCAN_FACES, "Scan Faces"),
        (JOB_TRAIN_FACES, "Train Faces"),
        (JOB_CLUSTER_ALL_FACES, "Find Similar Faces"),
        (JOB_DELETE_MISSING_PHOTOS, "Delete Missing Photos"),
        (JOB_DOWNLOAD_PHOtoS, "Download Selected Photos"),
        (JOB_DOWLOAD_MODELS, "Download Models"),
    )

    job_id = models.CharField(max_length=36, unique=True, db_index=True)

    job_type = models.PositiveIntegerField(choices=JOB_TYPES)

    finished = models.BooleanField(default=False, blank=False, null=False)

    failed = models.BooleanField(default=False, blank=False, null=False)

    queued_at = models.DateTimeField(default=datetime.now, null=False)

    started_at = models.DateTimeField(null=True)

    finished_at = models.DateTimeField(null=True)

    result = models.JSONField(default=get_default_job_result, blank=False, null=False)

    started_by = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )


def update_or_create_job(job_id, job_type, started_by):
    """Create or update a job based on the provided job_id, job_type, and user who
    started the job."""

    if Job.objects.filter(job_id=job_id).exists():
        job = Job.objects.get(job_id=job_id)
        job.started_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
    else:
        job = Job.objects.create(
            started_by=started_by,
            job_id=job_id,
            queued_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            started_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            job_type=job_type,
        )

    return job
