"""Import all models for easier importing."""

from api.models.cluster import Cluster
from api.models.face import Face
from api.models.person import Person
from api.models.photos import Photos
from api.models.user import User

__all__ = [
    "Cluster",
    "Face",
    "Person",
    "Photos",
    "User",
]
