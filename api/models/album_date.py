"""Create Date Albums model for database."""

from django.db import models

from api.models.photos import Photos
from api.models.user import User, get_deleted_user


class AlbumDate(models.Model):
    title = models.CharField(blank=True, null=True, max_length=512, db_index=True)
    date = models.DateField(db_index=True, null=True)
    photos = models.ManyToManyField(Photos)
    favorited = models.BooleanField(default=False, db_index=True)
    location = models.JSONField(blank=True, db_index=True, null=True)
    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )
    objects = models.Manager()

    class Meta:
        unique_together = ("owner", "date")

    def __str__(self):
        return str(self.date) + " (" + str(self.owner) + ")"

    def ordered_photos(self):
        return self.photos.all().ordered_by("-exif_timestamp")


def get_or_create_album_date(date, owner):
    try:
        return AlbumDate.objects.get_or_create(date=date, owner=owner)[0]
    except AlbumDate.MultipleObjectsReturned:
        return AlbumDate.objects.filter(date=date, owner=owner).first()


def get_album_date(date, owner):
    try:
        return AlbumDate.objects.get(date=date, owner=owner)
    except Exception:
        return None


def get_album_no_date(owner):
    return AlbumDate.objects.get_or_create(date=None, owner=owner)[0]
