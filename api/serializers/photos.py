"""Photos serializer."""

import json
import pytz

from rest_framework import serializers

from api.image_similarity import search_similar_images
from api.models import Photos
from api.serializers.simple import UserSimpleSerializer
from api.serializers.user import UserSerializer


utc = pytz.UTC


class PhotoHashListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photos
        fields = ["image_hash", "video"]


class PhotosSerializer(serializers.ModelSerializer):
    """Photos serializer."""

    optimized_image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    similar_photos = serializers.SerializerMethodField()
    captions_json = serializers.SerializerMethodField()
    people = serializers.SerializerMethodField()
    image_path = serializers.SerializerMethodField()
    owner = UserSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = Photos
        fields = (
            "exif_gps_lat",
            "exif_gps_lon",
            "exif_timestamp",
            "search_captions",
            "search_location",
            "captions_json",
            "optimized_image_url",
            "thumbnail_url",
            "people",
            "exif_json",
            "geolocation_json",
            "image_path",
            "image_hash",
            "rating",
            "hidden",
            "deleted",
            "similar_photos",
            "owner",
            "video",
            "size",
            "height",
            "width",
        )

    def get_similar_photos(self, obj) -> list:
        """Retrieves a list of similar photos based on the given `obj` and `threshold` value.

        Parameters:
            obj (Photo): The photo object for which to retrieve similar photos.
            threshold (int, optional): The threshold value for similarity. Defaults to 90.

        Returns:
            list: A list of dictionaries containing the image hash and type of each similar photo.
                Each dictionary has the following keys:
                - image_hash (str): The image hash of the similar photo.
                - type (str): The type of the similar photo (either "image" or "video").

                If no similar photos are found, an empty list is returned.
        """

        res = search_similar_images(obj.owner, obj, threshold=90)
        arr = []

        if len(res) > 0:
            photos = Photos.objects.filter(image_hash__in=arr).all()
            res = []

            for photo in photos:
                photo_type = "image"

                if photo.video:
                    photo_type = "video"

                res.append({"image_hash": photo.image_hash, "type": photo_type})

            return res
        else:
            return []

    def get_captions_json(self, obj) -> dict:
        """Get the captions JSON for the given object.

        Args:
            obj (object): The object for which to retrieve the captions JSON.
        Returns:
            dict: The captions JSON for the object. If the object's `captions_json`
            attribute is not empty and has a length greater than 0, the `captions_json`
            attribute is returned. Otherwise, an empty dictionary with the following structure
            is returned:
            {
                "im2txt": "",
                "places365": {
                    "attributes": [],
                    "categories": [],
                    "environment": [],
                },
            }
        """

        if obj.captions_json and len(obj.captions_json) > 0:
            return obj.captions_json
        else:
            empty_array = {
                "im2txt": "",
                "places365": {
                    "attributes": [],
                    "categories": [],
                    "environment": [],
                },
            }

            return empty_array

    def get_image_path(self, obj) -> list[str]:
        """Get the paths of all files associated with the given object.

        Args:
            obj (object): The object for which to retrieve the file paths.

        Returns:
            list[str]: A list of file paths associated with the object. If an exception occurs,
            returns ["Missing"].
        """

        try:
            paths = []

            for file in obj.files.all():
                paths.append(file.path)

            return paths
        except ValueError:
            return ["Missing"]

    def get_optimized_image_url(self, obj) -> str:
        """Retrieves the optimized image URL for the given object.

        Args:
            obj (string): The object for which to retrieve the optimized image URL.

        Returns:
            str: The optimized image URL for the object.
        """

        try:
            return obj.optimized_image.url
        except ValueError:
            return None

    def get_thumbnail_url(self, obj) -> str:
        """Retrieves the thumbnail URL for the given object.

        Args:
            obj (string): The object for which to retrieve the thumbnail URL.

        Returns:
            str: The thumbnail URL for the object.
        """

        try:
            return obj.thumbnail.url
        except ValueError:
            return None

    def get_geolocation(self, obj) -> dict:
        """Retrieves the geolocation for the given object.

        Args:
            obj (string): The object for which to retrieve the geolocation.

        Returns:
            dict: The geolocation for the object.
        """

        if obj.geolocation_json:
            return json.loads(obj.geolocation_json)
        else:
            return None

    def get_people(self, obj) -> list:
        """Retrieves a list of people associated with the given object.

        Args:
            obj (string): The object for which to retrieve the people.

        Returns:
            list: The list of people associated with the object.
        """

        return [
            {"name": f.person.name, "face_url": f.image.url, "face_id": f.id}
            for f in obj.faces.all()
        ]


class PhotoEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photos
        fields = (
            "image_hash",
            "hidden",
            "rating",
            "deleted",
            "video",
            "exif_timestamp",
            "timestamp",
        )

    def update(self, instance, validated_data):
        # photo can only update the following
        if "exif_timestamp" in validated_data:
            instance.timestamp = validated_data.pop("exif_timestamp")
            instance.save()
            instance._extract_date_time_from_exif()

        return instance


class PhotoSummarySerializer(serializers.ModelSerializer):
    """Photo summary serializer."""

    id = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    video_length = serializers.SerializerMethodField()
    exif_timestamp = serializers.SerializerMethodField()
    owner = UserSimpleSerializer()

    class Meta:
        model = Photos
        fields = (
            "id",
            "url",
            "location",
            "date",
            "video_length",
            "owner",
            "rating",
            "exif_timestamp",
            "height",
            "width",
        )

    def get_id(self, obj) -> str:
        """Returns photo's hash."""

        return obj.image_hash

    def get_url(self, obj) -> str:
        """Returns photo's hash."""

        return obj.image_hash

    def get_location(self, obj) -> str:
        """Returns photo's location."""

        if obj.search_location:
            return obj.search_location
        else:
            return ""

    def get_date(self, obj) -> str:
        """Returns photo's date."""

        if obj.exif_timestamp:
            return obj.exif_timestamp.isoformat()
        else:
            return ""

    def get_exif_timestamp(self, obj) -> str:
        """Returns photo's date."""

        if obj.exif_timestamp:
            return obj.exif_timestamp.isoformat()
        else:
            return ""

    def get_video_length(self, obj) -> int:
        """Get's video length if it exists."""

        if obj.video_length:
            return obj.video_length
        else:
            return ""

    def get_type(self, obj) -> str:
        """Returns if object is a photo or video."""

        if obj.video:
            return "video"

        return "image"


class PhotoDetailsSummarySerializer(serializers.ModelSerializer):
    """Details summary serializer."""

    photo_summary = serializers.SerializerMethodField()
    processing = serializers.SerializerMethodField()

    class Meta:
        model = Photos
        fields = ("photo_summary", "processing")

    def get_photo_summary(self, obj) -> PhotoSummarySerializer:
        """Returns photo summary.

        Args:
            obj (string): The object for which to retrieve the summary.

        Returns:
            PhotoSummarySerializer: The summary for the object.
        """

        return PhotoSummarySerializer(obj.get()).data

    def get_processing(self, obj) -> bool:
        """Returns if photo is being processed.

        Args:
            obj (string): The object for which to retrieve the processing status.

        Returns:
            bool: The processing status for the object.
        """

        return obj.get().dominant_color is None


class PhotosGroupedByDate:
    """Grouped photos by date."""

    def __init__(self, location, date, photos):
        self.photos = photos
        self.date = date
        self.location = location


def get_photos_ordered_by_date(photos):
    """
    Function to group photos by date based on exif timestamp and create a list of PhotosGroupedByDate objects.
    Parameters:
        photos (list): List of photo objects.
    Returns:
        list: List of PhotosGroupedByDate objects representing grouped photos by date.
    """

    from collections import defaultdict

    groups = defaultdict(list)

    for photo in photos:
        if photo.exif_timestamp:
            groups[photo.exif_timestamp.date().strftime("%Y-%m-%d")].append(photo)
        else:
            groups[photo.exif_timestamp].append(photo)

    grouped_photo = list(groups.values())
    result = []
    no_timestamp_photos = []

    for group in grouped_photo:
        location = ""

        if group[0].exif_timestamp:
            date = group[0].exif_timestamp.date().strftime("%Y-%m-%d")
            result.append(PhotosGroupedByDate(location, date, group))
        else:
            date = "No Timestamp"
            no_timestamp_photos = PhotosGroupedByDate(location, date, group)

    # Add no timestamp last
    if no_timestamp_photos != []:
        result.append(no_timestamp_photos)

    return result


class GroupedPhotosSerializer(serializers.ModelSerializer):
    """Grouped photos serializer."""

    items = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Photos
        fields = ["date", "location", "items"]

    def get_date(self, obj) -> str:
        """Return photo's date."""

        return obj.date

    def get_location(self, obj) -> str:
        """Return photo's location."""

        return obj.location

    def get_items(self, obj) -> PhotoSummarySerializer(many=True):  # type: ignore
        """Return the photos in the group."""

        return PhotoSummarySerializer(obj.photos, many=True).data
