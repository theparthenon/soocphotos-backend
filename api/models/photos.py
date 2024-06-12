"""Create Photos model for database."""

from django.db import models

from .user import User, get_deleted_user


class Photos(models.Model):
    """Photos model initialization."""

    image_hash = models.CharField(primary_key=True, max_length=64, null=False)
    image_size = models.BigIntegerField(default=0)
    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )

    original_image = models.ImageField(upload_to="originals")
    optimized_image = models.ImageField(upload_to="optimized")
    thumbnail = models.ImageField(upload_to="thumbnails")
    added_on = models.DateTimeField(auto_now_add=True)

    captions_json = models.JSONField(blank=True, null=True, db_index=True)
    geolocation_json = models.JSONField(blank=True, null=True, db_index=True)
    exif_json = models.JSONField(blank=True, null=True)

    exif_gps_lat = models.FloatField(blank=True, null=True)
    exif_gps_lon = models.FloatField(blank=True, null=True)
    exif_timestamp = models.DateTimeField(blank=True, null=True)

    search_captions = models.TextField(blank=True, null=True, db_index=True)
    search_location = models.TextField(blank=True, null=True, db_index=True)

    rating = models.IntegerField(default=0, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)
    hidden = models.BooleanField(default=False, db_index=True)
    video = models.BooleanField(default=False)
    video_length = models.TextField(blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.image_hash} - {self.owner} - {self.added_on} - {self.rating}"
