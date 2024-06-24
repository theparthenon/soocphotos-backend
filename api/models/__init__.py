"""Import all models for easier importing."""

from api.models.albums import Albums
from api.models.album_date import AlbumDate
from api.models.album_place import AlbumPlace
from api.models.album_thing import AlbumThing
from api.models.cluster import Cluster
from api.models.face import Face
from api.models.file import File
from api.models.job import Job
from api.models.person import Person
from api.models.photos import Photos
from api.models.user import User

__all__ = [
    "Albums",
    "AlbumDate",
    "AlbumPlace",
    "AlbumThing",
    "Cluster",
    "Face",
    "File",
    "Job",
    "Person",
    "Photos",
    "User",
]
