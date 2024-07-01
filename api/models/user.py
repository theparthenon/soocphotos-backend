"""Create User model for database."""

import pytz

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from api.date_time_extractor import DEFAULT_RULES_JSON


def get_default_config_datetime_rules():  # This is a callable
    """Returns default rules in json format."""

    return DEFAULT_RULES_JSON


def get_default_llm_settings():
    """Default settings for LLM model."""

    return {
        "enabled": False,
        "add_person": False,
        "add_location": False,
        "add_keywords": False,
        "add_camera": False,
        "add_lens": False,
        "add_album": False,
        "sentiment": 0,
        "custom_prompt": "",
        "custom_prompt_enabled": False,
    }


class User(AbstractUser):
    """User Model initialization."""

    photo_count = models.IntegerField(default=0)
    confidence = models.FloatField(default=0.1, db_index=True)
    confidence_person = models.FloatField(default=0.9)
    image_scale = models.FloatField(default=1)
    avatar = models.ImageField(upload_to="avatars", null=True, blank=True)
    transcode_videos = models.BooleanField(default=False)
    favorite_min_rating = models.IntegerField(
        default=settings.DEFAULT_FAVORITE_MIN_RATING, db_index=True
    )
    llm_settings = models.JSONField(default=get_default_llm_settings)
    datetime_rules = models.JSONField(default=get_default_config_datetime_rules)
    default_timezone = models.TextField(
        choices=[(x, x) for x in pytz.all_timezones],
        default="UTC",
    )
    scan_directory = models.CharField(max_length=512, db_index=True)

    class FaceRecogniton(models.TextChoices):
        """Options for facial recognition model."""

        HOG = "HOG"
        CNN = "CNN"

    face_recognition_model = models.TextField(
        choices=FaceRecogniton.choices, default=FaceRecogniton.HOG
    )
    min_cluster_size = models.IntegerField(default=0)
    confidence_unknown_face = models.FloatField(default=0.5)
    min_samples = models.IntegerField(default=1)
    cluster_selection_epsilon = models.FloatField(default=0.05)

    class CaptioningModel(models.TextChoices):
        """Options for captioning model."""

        NONE = "None"
        IM2TXT_ONNX = "im2txt_onnx"
        BLIP = "blip_base_capfilt_large"

    captioning_model = models.TextField(
        choices=CaptioningModel.choices, default=CaptioningModel.IM2TXT_ONNX
    )

    class SaveMetadata(models.TextChoices):
        """Choices for save metadata option."""

        OFF = "OFF"
        MEDIA_FILE = "MEDIA_FILE"
        SIDECAR_FILE = "SIDECAR_FILE"

    save_metadata_to_disk = models.TextField(
        choices=SaveMetadata.choices, default=SaveMetadata.OFF
    )


def get_admin_user():
    """Retrieves the admin user from the database."""

    return User.objects.get(is_superuser=True)


def get_deleted_user():
    """Retrieves the deleted user, or creates it if it doesn't exist."""

    deleted_user: User = User.objects.get_or_create(username="deleted")[0]
    if deleted_user.is_active is not False:
        deleted_user.is_active = False
        deleted_user.save()

    return deleted_user
