from django.db import models

from api.models.photos import Photos
from api.models.user import User, get_deleted_user


class AlbumUser(models.Model):
    title = models.CharField(max_length=512)
    created_on = models.DateTimeField(auto_now=True, db_index=True)
    photos = models.ManyToManyField(Photos)
    favorited = models.BooleanField(default=False, db_index=True)
    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )
    cover_photo = models.ForeignKey(
        Photos,
        related_name="albums_user",
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
    )

    class Meta:
        unique_together = ("title", "owner")
