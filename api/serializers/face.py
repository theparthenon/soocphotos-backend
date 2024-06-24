"""Face serializer."""

from rest_framework import serializers

from api.models import Face, Person


class PersonFaceListSerializer(serializers.ModelSerializer):
    """Class for serializing person faces."""

    face_url = serializers.SerializerMethodField()

    class Meta:
        model = Face
        fields = [
            "id",
            "image",
            "face_url",
            "photo",
            "timestamp",
            "person_label_probability",
        ]

    def get_face_url(self, obj) -> str:
        """
        Returns the URL of the image associated with the given object.
        Parameters:
            obj (object): The object for which to retrieve the image URL.
        Returns:
            str: The URL of the image.
        """

        return obj.image.url


class IncompletePersonFaceListSerializer(serializers.ModelSerializer):
    """Class for serializing incomplete person faces."""

    face_count = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "name", "kind", "face_count"]

    def get_face_count(self, obj) -> int:
        """
        Returns the number of faces associated with the given object.

        Args:
            obj (object): The object for which to retrieve the face count.

        Returns:
            int: The number of faces.
        """
        if obj and obj.viewable_face_count:
            return obj.viewable_face_count
        else:
            return 0


class FaceListSerializer(serializers.ModelSerializer):
    """Class for serializing faces."""

    person_name = serializers.SerializerMethodField()
    face_url = serializers.SerializerMethodField()

    class Meta:
        model = Face
        fields = [
            "id",
            "image",
            "face_url",
            "timestamp",
            "photo",
            "person",
            "person_label_probability",
            "person_name",
        ]

    def get_face_url(self, obj) -> str:
        """
        Returns the URL of the image associated with the given object.
        Parameters:
            obj (object): The object for which to retrieve the image URL.
        Returns:
            str: The URL of the image.
        """

        return obj.image.url

    def get_person_name(self, obj) -> str:
        """
        Returns the name of the person associated with the given object.

        Args:
            obj (object): The object for which to retrieve the person name.

        Returns:
            str: The name of the person.
        """
        return obj.person.name
