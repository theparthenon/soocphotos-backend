"""User serializer."""

from rest_framework import serializers

from api.models import Photos, User


class UserSerializer(serializers.ModelSerializer):
    """User serializer."""

    photo_count = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        extra_kwargs = {
            "password": {"write_only": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "confidence": {"required": False},
            "confidence_person": {"required": False},
            "semantic_search_topk": {"required": False},
            "favorite_min_rating": {"required": False},
        }
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "photo_count",
            "avatar_url",
            "password",
            "confidence",
            "confidence_person",
            "semantic_search_topk",
            "favorite_min_rating",
            "transcode_videos",
            "date_joined",
            "is_superuser",
            "llm_settings",
            "face_recognition_model",
            "min_cluster_size",
            "confidence_unknown_face",
            "min_samples",
            "cluster_selection_epsilon",
        ]

    def get_photo_count(self, obj) -> int:
        """Returns the number of photos owned by the user."""

        return Photos.objects.filter(owner=obj).count()

    def get_avatar_url(self, obj) -> str or None:  # type: ignore
        """Returns the URL of the user's avatar."""

        try:
            return obj.avatar.url
        except ValueError:
            return None
