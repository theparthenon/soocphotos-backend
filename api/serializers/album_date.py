"""Album Date serializer."""

from rest_framework import serializers

from api.models import AlbumDate


class IncompleteAlbumDateSerializer(serializers.ModelSerializer):
    """Class for serializing incomplete Album Dates."""

    id = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    incomplete = serializers.SerializerMethodField()
    number_of_items = serializers.SerializerMethodField("get_number_of_items")
    items = serializers.SerializerMethodField()

    class Meta:
        model = AlbumDate
        fields = [
            "id",
            "date",
            "location",
            "number_of_items",
            "items",
            "incomplete",
        ]

    def get_id(self, obj) -> str:
        """Get the id of the date album."""

        return str(obj.id)

    def get_date(self, obj) -> str:
        """Get the date of the date album."""

        if obj.date:
            return obj.date.isoformat()
        else:
            return None

    def get_items(self, obj) -> list:
        """Get the items of the date album."""

        return []

    def get_incomplete(self, obj) -> bool:
        """Get the incomplete status of the date album."""

        return True

    def get_number_of_items(self, obj) -> int:
        """Get the number of items in the date album."""

        if obj and obj.photo_count:
            return obj.photo_count
        else:
            return 0

    def get_location(self, obj) -> dict:
        """Get the location of the date album."""

        if obj and obj.location:
            return obj.location["places"][0]
        else:
            return ""


class AlbumDateSerializer(serializers.ModelSerializer):
    """Class for serializing Date Albums."""

    id = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    incomplete = serializers.SerializerMethodField()
    number_of_items = serializers.SerializerMethodField("get_number_of_items")
    items = serializers.SerializerMethodField()

    class Meta:
        model = AlbumDate
        fields = ["id", "date", "location", "number_of_items", "incomplete", "items"]

    def get_id(self, obj) -> str:
        """Get the id of the date album."""

        return str(obj.id)

    def get_date(self, obj) -> str:
        """Get the date of the date album."""

        if obj.date:
            return obj.date.isoformat()
        else:
            return None

    def get_items(self, obj) -> list:
        """This method is removed as we're directly including paginated photos in the response."""
        pass

    def get_incomplete(self, obj) -> bool:
        """Get the incomplete status of the date album."""

        return False

    def get_number_of_items(self, obj) -> int:
        """This will also get added in the response."""
        pass

    def get_location(self, obj) -> dict:
        """Get the location of the date album."""

        if obj and obj.location:
            return obj.location["places"][0]
        else:
            return ""
