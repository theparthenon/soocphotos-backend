"""Create person model for database."""

import datetime
import pytz
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Prefetch

from api.models.photos import Photos
from api.models.user import User

utc = pytz.UTC  # pylint: disable=invalid-name


class Person(models.Model):
    """Person model initialization."""

    UNKNOWN_PERSON_NAME = "Unknown - Other"
    KIND_USER = "USER"
    KIND_CLUSTER = "CLUSTER"
    KIND_UNKNOWN = "UNKNOWN"
    KIND_CHOICES = (
        (KIND_USER, "User Labelled"),
        (KIND_CLUSTER, "Cluster ID"),
        (KIND_UNKNOWN, "Unknown Person"),
    )
    name = models.CharField(
        blank=False, max_length=128, validators=[MinLengthValidator(1)], db_index=True
    )
    kind = models.CharField(choices=KIND_CHOICES, max_length=10)
    cover_photo = models.ForeignKey(
        Photos, related_name="person", on_delete=models.SET_NULL, blank=False, null=True
    )
    cover_face = models.ForeignKey(
        "Face",
        related_name="face",
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
    )
    face_count = models.IntegerField(default=0)
    cluster_owner = models.ForeignKey(
        User,
        related_name="owner",
        on_delete=models.SET_NULL,
        default=None,
        null=True,
    )
    date_of_birth = models.DateField(null=True)
    date_of_death = models.DateField(null=True)
    notes = models.TextField(null=True)

    def __str__(self):
        return (
            self.name
            + " ("
            + self.kind
            + ")"
            + " ("
            + str(self.id)
            + ")"
            + " ("
            + str(self.cluster_owner)
            + ")"
        )

    def _calculate_face_count(self):
        confidence_person = (
            User.objects.filter(id=self.cluster_owner.id).first().confidence_person
        )
        self.face_count = self.faces.filter(
            photo__hidden=False,
            photo__deleted=False,
            photo__owner=self.cluster_owner.id,
            person_label_probability__gte=confidence_person,
        ).count()
        self.save()

    def _set_default_cover_photo(self):
        if not self.cover_photo:
            self.cover_photo = self.faces.first().photo  # pylint: disable=no-member
            self.cover_face = self.faces.first()  # pylint: disable=no-member
            self.save()

    def get_photos(self, owner):
        """Retrieves photos associated with the specified owner, sorted by exif
        timestamp in descending order."""

        faces = list(
            self.faces.prefetch_related(
                Prefetch(
                    "photo",
                    queryset=Photos.objects.exclude(image_hash=None)
                    .filter(hidden=False, owner=owner)
                    .order_by("-exif_timestamp")
                    .only(
                        "image_hash",
                        "exif_timestamp",
                        "rating",
                        "owner__id",
                        "hidden",
                    )
                    .prefetch_related("owner"),
                )
            )
        )

        photos = [face.photo for face in faces if hasattr(face.photo, "owner")]
        photos.sort(
            key=lambda x: x.exif_timestamp
            or utc.localize(datetime.datetime.min),  # pylint: disable=E1120
            reverse=True,
        )
        return photos


def get_unknown_person(owner: User = None):
    """Retrieves the unknown person associated with the specified owner."""

    unknown_person: Person = Person.objects.get_or_create(
        name=Person.UNKNOWN_PERSON_NAME, cluster_owner=owner, kind=Person.KIND_UNKNOWN
    )[0]
    if unknown_person.kind != Person.KIND_UNKNOWN:
        unknown_person.kind = Person.KIND_UNKNOWN
        unknown_person.save()
    return unknown_person


def get_or_create_person(name, owner: User = None, kind: str = Person.KIND_UNKNOWN):
    """Gets person associated with the specified owner or creates a new one if none"""

    return Person.objects.get_or_create(name=name, cluster_owner=owner, kind=kind)[0]
