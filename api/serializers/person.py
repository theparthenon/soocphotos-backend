"""Person serializer."""

from django.db.models import Q
from rest_framework import serializers

from api.models import Person, Photos
from api.serializers.photos import GroupedPhotosSerializer, get_photos_ordered_by_date
from api.utils import logger


class GroupedPersonPhotosSerializer(serializers.ModelSerializer):
    """Serializer for grouped person photos."""

    id = serializers.SerializerMethodField()
    grouped_photos = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "name", "grouped_photos"]

    def get_id(self, obj) -> str:
        """Get the id of the person."""

        return str(obj.id)

    def get_grouped_photos(self, obj) -> GroupedPhotosSerializer(many=True):
        """Get the group of photos for the person."""

        user = None
        request = self.context.get("request")

        if request and hasattr(request, "user"):
            user = request.user

        grouped_photos = get_photos_ordered_by_date(obj.get_photos(user))
        res = GroupedPhotosSerializer(grouped_photos, many=True).data

        return res


class PersonSerializer(serializers.ModelSerializer):
    """Serializer for person model."""

    face_url = serializers.SerializerMethodField()
    face_photo_url = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    new_person_name = serializers.CharField(max_length=100, default="", write_only=True)
    cover_photo = serializers.CharField(max_length=100, default="", write_only=True)

    class Meta:
        model = Person
        fields = [
            "name",
            "face_count",
            "face_photo_url",
            "face_url",
            "video",
            "id",
            "new_person_name",
            "cover_photo",
        ]

    def get_face_url(self, obj) -> str:
        """Returns the URL of the image associated with the given object."""

        if obj.cover_face:
            return "/media/" + obj.cover_face.image.name

        if obj.faces.count() == 0:
            return ""

        return "/media/" + obj.faces.first().image.name

    def get_face_photo_url(self, obj) -> str:
        """Returns the URL of the image associated with the given object."""

        if obj.cover_photo:
            return obj.cover_photo.image_hash

        if obj.faces.count() == 0:
            return ""

        return obj.faces.first().photo.image_hash

    def get_video(self, obj) -> str:
        """Returns the video associated with the given object."""

        if obj.cover_photo:
            return obj.cover_photo.video

        if obj.faces.count() == 0:
            return "False"

        return obj.faces.first().photo.video

    def create(self, validated_data):
        """Creates a new person."""

        name = validated_data.pop("name")

        if len(name.strip()) == 0:
            raise serializers.ValidationError("Name cannot be empty")

        qs = Person.objects.filter(name=name)

        if qs.count() > 0:
            return qs[0]
        else:
            new_person = Person()
            new_person.name = name
            new_person.save()

            logger.info("Created person %d", new_person.id)

            return new_person

    def update(self, instance, validated_data):
        """Updates the given person."""

        if "new_person_name" in validated_data.keys():
            new_name = validated_data.pop("new_person_name")
            instance.name = new_name
            instance.save()

            return instance

        if "cover_photo" in validated_data.keys():
            image_hash = validated_data.pop("cover_photo")
            photo = Photos.objects.filter(image_hash=image_hash).first()
            instance.cover_photo = photo
            instance.cover_face = photo.faces.filter(person__name=instance.name).first()
            instance.save()

            return instance

        return instance

    def delete(self, validated_data, id):
        """Deletes the given person."""

        person_to_delete = Person.objects.filter(id=id).get()
        person_to_delete.delete()


class AlbumPersonListSerializer(serializers.ModelSerializer):
    """Serializer for album person list."""

    photo_count = serializers.SerializerMethodField()
    cover_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "name", "photo_count", "cover_photo_url"]

    def get_photo_count(self, obj) -> int:
        """Get the number of photos in the album."""

        return obj.filter(Q(person_label_is_inferred=False)).faces.count()

    def get_cover_photo_url(self, obj) -> str:
        """Get the URL of the first thumbnail in the album."""

        first_face = obj.faces.filter(Q(person_label_is_inferred=False)).first()

        if first_face:
            return first_face.photo.thumbnail.url
        else:
            return None

    def get_face_photo_url(self, obj) -> str:
        """Get the URL of the first face in the album."""

        first_face = obj.faces.filter(Q(person_label_is_inferred=False)).first()

        if first_face:
            return first_face.photo.image.url
        else:
            return None
