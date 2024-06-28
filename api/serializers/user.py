"""User serializer."""

import os

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.models import Photos, User
from api.utils import logger


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
            "scan_directory": {"required": False},
            "confidence": {"required": False},
            "confidence_person": {"required": False},
            "favorite_min_rating": {"required": False},
            "save_metadata_to_disk": {"required": False},
        }
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "scan_directory",
            "photo_count",
            "avatar",
            "avatar_url",
            "password",
            "confidence",
            "confidence_person",
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
            "save_metadata_to_disk",
            "datetime_rules",
            "default_timezone",
        ]

    def update(self, instance, validated_data):
        # user can only update the following
        if "password" in validated_data:
            password = validated_data.pop("password")

            if password != "":
                instance.set_password(password)

        if "avatar" in validated_data:
            instance.avatar = validated_data.pop("avatar")
            instance.save()

        if "email" in validated_data:
            instance.email = validated_data.pop("email")
            instance.save()

        if "first_name" in validated_data:
            instance.first_name = validated_data.pop("first_name")
            instance.save()

        if "last_name" in validated_data:
            instance.last_name = validated_data.pop("last_name")
            instance.save()

        if "transcode_videos" in validated_data:
            instance.transcode_videos = validated_data.pop("transcode_videos")
            instance.save()

        if "confidence" in validated_data:
            instance.confidence = validated_data.pop("confidence")
            instance.save()
            logger.info("Updated confidence for user to: %d", instance.confidence)

        if "confidence_person" in validated_data:
            instance.confidence_person = validated_data.pop("confidence_person")
            instance.save()
            logger.info(
                "Updated person album confidence for user to: %s",
                instance.confidence_person,
            )

        if "favorite_min_rating" in validated_data:
            new_favorite_min_rating = validated_data.pop("favorite_min_rating")
            instance.favorite_min_rating = new_favorite_min_rating
            instance.save()
            logger.info(
                "Updated favorite_min_rating for user to: %s", instance.favorite_min_rating
            )

        if "save_metadata_to_disk" in validated_data:
            instance.save_metadata_to_disk = validated_data.pop("save_metadata_to_disk")
            instance.save()
            logger.info(
                "Updated save_metadata_to_disk for user to: %s",
                instance.save_metadata_to_disk,
            )

        if "datetime_rules" in validated_data:
            new_datetime_rules = validated_data.pop("datetime_rules")
            instance.datetime_rules = new_datetime_rules
            instance.save()
            logger.info("Updated datetime_rules for user to: %s", instance.datetime_rules)

        if "default_timezone" in validated_data:
            new_default_timezone = validated_data.pop("default_timezone")
            instance.default_timezone = new_default_timezone
            instance.save()
            logger.info(
                "Updated default_timezone for user to: %s", instance.default_timezone
            )

        if "face_recognition_model" in validated_data:
            instance.face_recognition_model = validated_data.pop(
                "face_recognition_model"
            )
            instance.save()

        if "min_cluster_size" in validated_data:
            instance.min_cluster_size = validated_data.pop("min_cluster_size")
            instance.save()

        if "confidence_unknown_face" in validated_data:
            instance.confidence_unknown_face = validated_data.pop(
                "confidence_unknown_face"
            )
            instance.save()

        if "min_samples" in validated_data:
            instance.min_samples = validated_data.pop("min_samples")
            instance.save()

        if "cluster_selection_epsilon" in validated_data:
            instance.cluster_selection_epsilon = validated_data.pop(
                "cluster_selection_epsilon"
            )
            instance.save()

        if "llm_settings" in validated_data:
            instance.llm_settings = validated_data.pop("llm_settings")
            instance.save()

        return instance

    def get_photo_count(self, obj) -> int:
        """Returns the number of photos owned by the user."""

        return Photos.objects.filter(owner=obj).count()

    def get_avatar_url(self, obj) -> str or None:  # type: ignore
        """Returns the URL of the user's avatar."""

        try:
            return obj.avatar.url
        except ValueError:
            return None


class SignupUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        extra_kwargs = {
            "username": {"required": True},
            "password": {
                "write_only": True,
                "required": True,
                "min_length": 3,  # configurable min password length?
            },
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "is_superuser": {"write_only": True},
        }
        fields = (
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "is_superuser",
        )

    def create(self, validated_data):
        should_be_superuser = User.objects.filter(is_superuser=True).count() == 0
        user = super().create(validated_data)
        user.set_password(validated_data.pop("password"))
        user.is_staff = should_be_superuser
        user.is_superuser = should_be_superuser
        user.save()
        return user


class DeleteUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = "__all__"


class ManageUserSerializer(serializers.ModelSerializer):
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "username",
            "confidence",
            "last_login",
            "date_joined",
            "photo_count",
            "id",
            "favorite_min_rating",
            "save_metadata_to_disk",
            "email",
            "first_name",
            "last_name",
            "password",
            "scan_directory",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "scan_directory": {"required": False},
        }

    def get_photo_count(self, obj) -> int:
        return Photos.objects.filter(owner=obj).count()

    def update(self, instance: User, validated_data):
        if "password" in validated_data:
            password = validated_data.pop("password")
            if password != "":
                instance.set_password(password)

        if "username" in validated_data:
            username = validated_data.pop("username")
            if username != "":
                other_user = User.objects.filter(username=username).first()
                if other_user is not None and other_user != instance:
                    raise ValidationError("User name is already taken")

            instance.username = username

        if "email" in validated_data:
            email = validated_data.pop("email")
            instance.email = email

        if "first_name" in validated_data:
            first_name = validated_data.pop("first_name")
            instance.first_name = first_name

        if "last_name" in validated_data:
            last_name = validated_data.pop("last_name")
            instance.last_name = last_name

        if "scan_directory" in validated_data:
            new_scan_directory = validated_data.pop("scan_directory")

            if new_scan_directory != "":
                if os.path.exists(new_scan_directory):
                    instance.scan_directory = new_scan_directory
                    logger.info(
                        "Updated scan directory for user to: %s", instance.scan_directory
                    )
                else:
                    raise ValidationError("Scan directory does not exist")

        instance.save()
        return instance
