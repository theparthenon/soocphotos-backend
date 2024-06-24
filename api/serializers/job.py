"""Job serializer."""

from rest_framework import serializers

from api.models import Job
from api.serializers.simple import UserSimpleSerializer


class JobSerializer(serializers.ModelSerializer):
    """Job serializer."""

    job_type_str = serializers.SerializerMethodField()
    started_by = UserSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = Job
        fields = [
            "job_id",
            "queued_at",
            "finished",
            "finished_at",
            "started_at",
            "failed",
            "job_type_str",
            "job_type",
            "started_by",
            "result",
            "id",
        ]

    def get_job_type_str(self, obj) -> str:
        """Returns the job type as a string."""

        return dict(Job.JOB_TYPES)[obj.job_type]
