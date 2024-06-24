"""Create Albums model for database."""

from django.db import models

from api.models.photos import Photos


class Albums(models.Model):
    """Albums model initialization."""

    title = models.CharField(max_length=512)
    created_on = models.DateTimeField(auto_now=True, db_index=True)
    photos = models.ManyToManyField(Photos)
    favorited = models.BooleanField(default=False, db_index=True)
    cover_photo = models.ForeignKey(
        Photos,
        related_name="album_user",
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
    )

    def __str__(self):
        return str(self.title)
