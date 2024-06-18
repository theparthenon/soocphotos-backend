"""Simple versions of serializers."""

from rest_framework.serializers import ModelSerializer

from api.models import Photos, User


class PhotoSimpleSerializer(ModelSerializer):
    """Simple version of the photo serializer."""

    class Meta:
        model = Photos
        fields = (
            "image_hash",
            "rating",
            "exif_timestamp",
            "video",
            "geolocation_json",
            "exif_gps_lat",
            "exif_gps_lon",
            "thumbnail",
        )


class PhotoSuperSimpleSerializer(ModelSerializer):
    """A super simple version of the photo serializer."""

    class Meta:
        model = Photos
        fields = ("image_hash", "rating", "hidden", "exif_timestamp", "video")


class UserSimpleSerializer(ModelSerializer):
    """Simple version of the user serializer."""

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")
