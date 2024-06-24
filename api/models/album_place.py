"""Create Album Place model for database."""

from django.db import models

from api.models.photos import Photos
from api.models.user import User, get_deleted_user


class AlbumPlace(models.Model):
    """Album Place model initialization."""

    title = models.CharField(max_length=512, db_index=True)
    photos = models.ManyToManyField(Photos)
    geolocation_level = models.IntegerField(db_index=True, null=True)
    favorited = models.BooleanField(default=False, db_index=True)
    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )

    class Meta:
        unique_together = ("title", "owner")

    def __str__(self):
        return "%d: %s" % (self.id, self.title)


def get_album_place(title, owner):
    return AlbumPlace.objects.get_or_create(title=title, owner=owner)[0]
