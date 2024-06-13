"""Create cluster model for database."""

import numpy as np
from django.core.exceptions import MultipleObjectsReturned
from django.db import models

from api.models.person import Person, get_unknown_person
from api.models.user import User, get_deleted_user
from api.utils import logger

UNKNOWN_CLUSTER_ID = -1
UNKNOWN_CLUSTER_NAME = "Other Unknown Cluster"


class Cluster(models.Model):
    """Cluster model initialization."""

    cluster_id = models.IntegerField(null=True)
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        related_name="clusters",
        blank=True,
        null=True,
    )
    mean_face_encoding = models.TextField()
    name = models.TextField(null=True)

    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None, null=True
    )

    def __str__(self):
        return f"{self.id}"

    def get_mean_encoding_array(self) -> np.ndarray:
        """Returns a NumPy array containing the mean face encoding for this cluster."""

        return np.frombuffer(bytes.fromhex(self.mean_face_encoding))

    def set_metadata(self, all_vectors):
        """Set metadata for the cluster based on all vectors."""

        self.mean_face_encoding = (
            Cluster.calculate_mean_face_encoding(all_vectors).tobytes().hex()
        )

    @staticmethod
    def get_or_create_cluster_by_name(user: User, name):
        """Get or create a cluster by name for a given user."""

        return Cluster.objects.get_or_create(owner=user, name=name)[0]

    @staticmethod
    def get_or_create_cluster_by_id(user: User, cluster_id: int):
        """Get or create a cluster by ID for a given user."""

        try:
            return Cluster.objects.get_or_create(owner=user, cluster_id=cluster_id)[0]
        except MultipleObjectsReturned:
            logger.error(
                "Multiple clusters found with id %d. Choosing first one", cluster_id
            )
            return Cluster.objects.filter(owner=user, cluster_id=cluster_id).first()

    @staticmethod
    def calculate_mean_face_encoding(all_encodings):
        """Calculate the mean face encoding from a list of face encodings."""

        return np.mean(a=all_encodings, axis=0, dtype=np.float64)


def get_unknown_cluster(user: User) -> Cluster:
    """Retrieve or create a cluster for an unknown person associated with the given user."""

    unknown_person: Person = get_unknown_person(user)
    unknown_cluster: Cluster = Cluster.get_or_create_cluster_by_id(
        user, UNKNOWN_CLUSTER_ID
    )
    if unknown_cluster.person is not unknown_person:
        unknown_cluster.person = unknown_person
        unknown_cluster.name = UNKNOWN_CLUSTER_NAME
        unknown_cluster.save()
    return unknown_cluster
