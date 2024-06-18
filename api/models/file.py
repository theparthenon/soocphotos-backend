"""Create file model for database."""

from django.db import models


from api.utils import calculate_hash, is_metadata, is_raw, is_video


class File(models.Model):
    """File model initialization."""

    IMAGE = 1
    VIDEO = 2
    METADATA_FILE = 3
    RAW_FILE = 4
    UNKNOWN = 5

    FILE_TYPES = (
        (IMAGE, "Image"),
        (VIDEO, "Video"),
        (METADATA_FILE, "Metadata File e.g. XMP"),
        (RAW_FILE, "Raw File"),
        (UNKNOWN, "Unknown"),
    )

    hash = models.CharField(primary_key=True, max_length=64, null=False)
    path = models.TextField(blank=True, null=True)
    type = models.PositiveIntegerField(
        blank=True,
        choices=FILE_TYPES,
    )
    missing = models.BooleanField(default=False)
    embedded_media = models.ManyToManyField("File")

    @staticmethod
    def create(path: str, user):
        """Create a file based on the provided `path` and `user`."""

        file = File()
        file.path = path
        file.hash = calculate_hash(user, path)
        file._find_out_type()  # pylint: disable=protected-access
        file.save()
        return file

    def _find_out_type(self):
        self.type = File.IMAGE
        if is_raw(self.path):
            self.type = File.RAW_FILE
        if is_video(self.path):
            self.type = File.VIDEO
        if is_metadata(self.path):
            self.type = File.METADATA_FILE
        self.save()
