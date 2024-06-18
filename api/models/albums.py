"""Create Albums model for database."""

from django.db import models

from api.models.photos import Photos


class Albums(models.Model):
    """Albums model initialization."""

    album_name = models.TextField()
    photos = models.ManyToManyField(Photos)

    def __str__(self):
        return str(self.album_name)
