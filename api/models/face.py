"""Create face model for database."""

import os
import numpy as np
from django.db import models
from django.dispatch import receiver

from api.models.cluster import Cluster
from api.models.person import Person, get_unknown_person
from api.models.photos import Photos


class Face(models.Model):
    """Face model initialization."""

    photo = models.ForeignKey(
        Photos, related_name="faces", on_delete=models.CASCADE, blank=False, null=True
    )
    image = models.ImageField(upload_to="faces", null=True)

    person = models.ForeignKey(
        Person, on_delete=models.DO_NOTHING, related_name="faces"
    )

    cluster = models.ForeignKey(
        Cluster,
        related_name="faces",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    person_label_is_inferred = models.BooleanField(default=False, db_index=True)
    person_label_probability = models.FloatField(default=0.0, db_index=True)

    location_top = models.IntegerField()
    location_bottom = models.IntegerField()
    location_left = models.IntegerField()
    location_right = models.IntegerField()

    encoding = models.TextField()

    @property
    def timestamp(self):
        """Returns the timestamp of the photo associated with this face, if it exists."""

        return self.photo.exif_timestamp if self.photo else None

    def __str__(self):
        return f"{self.id}"

    def get_encoding_array(self):
        """Returns a NumPy array containing the encoding of the face."""

        return np.frombuffer(bytes.fromhex(self.encoding))


@receiver(models.signals.post_delete, sender=Person)
def reset_person(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """Resets the person associated with the face."""

    instance.faces.update(person=get_unknown_person(instance.cluster_owner))


# From: https://stackoverflow.com/questions/16041232/django-delete-filefield
@receiver(models.signals.post_delete, sender=Face)
def auto_delete_file_on_delete(
    sender, instance, **kwargs
):  # pylint: disable=unused-argument
    """Deletes file from filesystem when corresponding `FileField` object is deleted."""

    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
