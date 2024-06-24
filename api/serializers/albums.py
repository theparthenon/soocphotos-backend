"""Album serializer."""

from rest_framework import serializers

from api.models import Albums, Photos
from api.serializers.photos import GroupedPhotosSerializer, get_photos_ordered_by_date
from api.serializers.simple import PhotoSuperSimpleSerializer
from api.utils import logger


class AlbumSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    grouped_photos = serializers.SerializerMethodField()

    class Meta:
        model = Albums
        fields = [
            "id",
            "title",
            "date",
            "location",
            "grouped_photos",
        ]

    def get_id(self, obj) -> int:
        return obj.id

    def get_grouped_photos(self, obj) -> GroupedPhotosSerializer(many=True):
        grouped_photos = get_photos_ordered_by_date(
            obj.photos.all().order_by("-exif_timestamp")
        )
        res = GroupedPhotosSerializer(grouped_photos, many=True).data

        return res

    def get_location(self, obj) -> str:
        for photo in obj.photos.all():
            if photo and photo.search_location:
                return photo.search_location

        return ""

    def get_date(self, obj) -> str:
        for photo in obj.photos.all():
            if photo and photo.exif_timestamp:
                return photo.exif_timestamp

            return ""


class AlbumEditSerializer(serializers.ModelSerializer):
    """Album edit serializer."""

    photos = serializers.PrimaryKeyRelatedField(
        many=True, read_only=False, queryset=Photos.objects.all()
    )
    removed_photos = serializers.ListField(
        child=serializers.CharField(max_length=100, default=""),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Albums
        fields = [
            "id",
            "title",
            "photos",
            "created_on",
            "favorited",
            "removed_photos",
            "cover_photo",
        ]

    def validate_photos(self, value):
        return [v.image_hash for v in value]

    def create(self, validated_data):
        title = validated_data["title"]
        image_hashes = validated_data["photos"]

        user = None
        request = self.context.get("request")

        if request and hasattr(request, "user"):
            user = request.user

        # check if an album exists with the given title and call the update method if it does
        instance, created = Albums.objects.get_or_create(title=title, owner=user)

        if not created:
            return self.update(instance, validated_data)

        photos = Photos.objects.in_bulk(image_hashes)

        for pk, obj in photos.items():
            instance.photos.add(obj)

        instance.save()

        logger.info("Created album %d with %d photos", instance.id, len(photos))

        return instance

    def update(self, instance, validated_data):
        if "title" in validated_data.keys():
            title = validated_data["title"]
            instance.title = title

            logger.info("Renamed album to %s", title)

        if "removed_photos" in validated_data.keys():
            image_hashes = validated_data["removed_photos"]
            photos_already_in_album = instance.photos.all()
            cnt = 0

            for obj in photos_already_in_album:
                if obj.image_hash in image_hashes:
                    cnt += 1
                    instance.photos.remove(obj)

            logger.info("Removed %d photos from album %d", cnt, instance.id)

        if "cover_photo" in validated_data.keys():
            cover_photo = validated_data["cover_photo"]
            instance.cover_photo = cover_photo

            logger.info("Changed cover photo to %s", cover_photo)

        if "photos" in validated_data.keys():
            image_hashes = validated_data["photos"]
            photos = Photos.objects.in_bulk(image_hashes)
            photos_already_in_album = instance.photos.all()
            cnt = 0

            for pk, obj in photos.items():
                if obj not in photos_already_in_album:
                    cnt += 1
                    instance.photos.add(obj)

            logger.info("Added %d photos to album %d", cnt, instance.id)

        instance.save()

        return instance


class AlbumListSerializer(serializers.ModelSerializer):
    """Album list serializer."""

    cover_photo = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = Albums
        fields = [
            "id",
            "title",
            "photo_count",
            "created_on",
            "favorited",
            "cover_photo",
        ]

    def get_cover_photo(self, obj) -> PhotoSuperSimpleSerializer:
        if obj.cover_photo:
            return PhotoSuperSimpleSerializer(obj.cover_photo).data

        return PhotoSuperSimpleSerializer(obj.photos.first()).data

    def get_photo_count(self, obj) -> int:
        try:
            return obj.photo_count
        except Exception:  # for when calling AlbumUserListSerializer(obj).data directly
            return obj.photos.count()
