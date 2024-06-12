"""Import all models for easier importing."""

from api.models.photos import Photos
from api.models.user import User

__all__ = [
    "Photos",
    "User",
]
