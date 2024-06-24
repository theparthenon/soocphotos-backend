"""User views."""

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils_api import path_to_dict
from api.date_time_extractor import DEFAULT_RULES_JSON, PREDEFINED_RULES_JSON
from api.models import User
from api.mixins.permissions_mixin import IsAdminOrSelf
from api.serializers.user import (
    DeleteUserSerializer,
    ManageUserSerializer,
    SignupUserSerializer,
    UserSerializer,
)
from api.utils import logger


class DefaultRulesView(APIView):
    """View to get default rules."""

    def get(self, request, format=None):
        """Get default rules."""

        return Response(DEFAULT_RULES_JSON)


class PredefinedRulesView(APIView):
    """View to get predefined rules."""

    def get(self, request, format=None):
        """Get predefined rules."""

        return Response(PREDEFINED_RULES_JSON)


class RootPathTreeView(APIView):
    """View to get root path tree."""

    def get(self, request, format=None):
        try:
            path = self.request.query_params.get("path")

            if path:
                res = [path_to_dict(path)]
            else:
                res = [path_to_dict(settings.DATA_ROOT)]

            return Response(res)
        except Exception as e:
            logger.exception(str(e))

            return Response({"message": str(e)})


# To-Do: This executes multiple querys per users
class UserViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = (
            User.objects.exclude(is_active=False)
            .only(
                "id",
                "username",
                "email",
                "transcode_videos",
                "confidence",
                "confidence_person",
                "first_name",
                "last_name",
                "date_joined",
                "avatar",
                "favorite_min_rating",
                "save_metadata_to_disk",
                "datetime_rules",
                "default_timezone",
                "is_superuser",
            )
            .order_by("id")
        )
        return queryset

    def get_serializer_class(self):
        if not self.request.user.is_authenticated and self.action == "create":
            return SignupUserSerializer

        return UserSerializer

    def get_permissions(self):
        permission_classes = [IsAdminUser]
        if self.action in ["list", "retrieve"]:
            permission_classes = [AllowAny]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [IsAdminOrSelf]
        return [p() for p in permission_classes]


class DeleteUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = DeleteUserSerializer
    permission_classes = (IsAdminUser,)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()

        if instance.is_superuser:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return super().destroy(request, *args, **kwargs)


class ManageUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = ManageUserSerializer
    permission_classes = (IsAdminUser,)

    def retrieve(self, *args, **kwargs):
        return super(ManageUserViewSet, self).retrieve(*args, **kwargs)

    def list(self, *args, **kwargs):
        return super(ManageUserViewSet, self).list(*args, **kwargs)
