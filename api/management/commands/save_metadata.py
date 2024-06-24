# pylint: disable=protected-access
"""Django manager integration for saving metadata to image files."""

from django.core.management.base import BaseCommand

from api.models import Photos


class Command(BaseCommand):
    """Django manager command."""

    help = "save metadata to image files (or XMP sidecar files)"

    def handle(self, *args, **kwargs):
        for photo in Photos.objects.all():
            photo._save_metadata()
