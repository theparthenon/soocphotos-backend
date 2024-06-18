# pylint: disable=redefined-builtin, unused-argument
"""Photos viewset."""

from django.db.models import Prefetch, Q
from rest_framework import filters, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.mixins.list_view_mixin import ListViewSet
from api.mixins.pagination_mixin import (
    HugeResultsSetPagination,
    RegularResultsSetPagination,
)
from api.mixins.permissions_mixin import IsOwnerOrReadOnly
from api.models import Photos
from api.models.user import User
from api.serializers.photos import (
    PhotoDetailsSummarySerializer,
    PhotosSerializer,
    PhotoSummarySerializer,
)
from api.utils import logger


class PhotosViewSet(ModelViewSet):
    """Main photos viewset."""

    serializer_class = PhotosSerializer
    pagination_class = HugeResultsSetPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = [
        "search_captions",
        "search_location",
        "faces__person__name",
        "exif_timestamp",
        "main_file__path",
    ]

    @action(
        detail=True,
        methods=["get"],
        name="summary",
        serializer_class=PhotoDetailsSummarySerializer,
    )
    def summary(self, request, pk):
        """Returns photo summary."""

        queryset = self.get_queryset().filter(image_hash=pk)

        if not queryset.exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = PhotoDetailsSummarySerializer(queryset, many=False)

        return Response(serializer.data)

    def get_permissions(self):
        if (
            self.action == "list"
            or self.action == "retrieve"
            or self.action == "summary"
        ):
            permission_classes = [IsAdminUser or IsOwnerOrReadOnly]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return Photos.objects.none()
        else:
            return Photos.objects.order_by("-exif_timestamp")

    def retrieve(self, *args, **kwargs):  # pylint: disable=useless-parent-delegation
        return super(PhotosViewSet, self).retrieve(*args, **kwargs)

    def list(self, *args, **kwargs):  # pylint: disable=useless-parent-delegation
        return super(PhotosViewSet, self).list(*args, **kwargs)


class RecentlyAddedPhotosViewSet(ListViewSet):
    """Recently added photos viewset."""

    serializer_class = PhotoSummarySerializer
    pagination_class = HugeResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        latest_date = (
            Photos.visible.filter(Q(owner=self.request.user))
            .only("added_on")
            .order_by("-added_on")
            .first()
            .added_on
        )
        queryset = Photos.visible.filter(
            Q(owner=self.request.user)
            & Q(
                added_on__year=latest_date.year,
                added_on__month=latest_date.month,
                added_on__day=latest_date.day,
            )
        ).order_by("-added_on")

        return queryset

    def list(self, *args, **kwargs):
        queryset = self.get_queryset()
        latest_date = (
            Photos.visible.filter(Q(owner=self.request.user))
            .only("added_on")
            .order_by("-added_on")
            .first()
            .added_on
        )
        serializer = PhotoSummarySerializer(queryset, many=True)

        return Response(
            {
                "date": latest_date,
                "results": serializer.data,
            }
        )


class PhotosWithoutTimestampViewSet(ListViewSet):
    """No timestamp photos viewset."""

    serializer_class = PhotoSummarySerializer
    pagination_class = RegularResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    search_filters = ["search_captions", "search_location", "faces__person__name"]

    def get_queryset(self):
        return (
            Photos.visible.filter(Q(exif_timestamp=None) & Q(owner=self.request.user))
            .prefetch_related(
                Prefetch(
                    "owner",
                    queryset=User.objects.only(
                        "id", "username", "first_name", "last_name"
                    ),
                ),
            )
            .order_by("added_on")
        )

    def list(self, *args, **kwargs):  # pylint: disable=useless-parent-delegation
        return super(PhotosWithoutTimestampViewSet, self).list(*args, **kwargs)


class SetPhotosDeleted(APIView):
    """Set photos deleted."""

    def post(self, request, format=None):
        """Handle the POST request to update the hidden/deleted status of photos
        based on the provided data."""

        data = dict(request.data)
        val_hidden = data["deleted"]
        image_hashes = data["image_hashes"]

        updated = []
        not_updated = []

        for image_hash in image_hashes:
            try:
                photo = Photos.objects.get(image_hash=image_hash)
            except Photos.DoesNotExist:
                logger.warning(
                    "Could not set photo %s to hidden. It does not exist.", image_hash
                )

                continue

            if photo.owner == request.user and photo.deleted != val_hidden:
                photo.deleted = val_hidden
                photo.save()
                updated.append(PhotosSerializer(photo).data)
            else:
                not_updated.append(PhotosSerializer(photo).data)

        if val_hidden:
            logger.info(
                "%d photos were set hidden. %d photos were already deleted.",
                len(updated),
                len(not_updated),
            )
        else:
            logger.info(
                "%d photos were set unhidden. %d photos were already recovered.",
                len(updated),
                len(not_updated),
            )

        return Response(
            {
                "status": True,
                "results": updated,
                "updated": updated,
                "not_updated": not_updated,
            }
        )


class SetPhotosFavorite(APIView):
    """Set photos favorite."""

    def post(self, request, format=None):
        """Handle the POST request to update the favorite status of photos based
        on the provided data."""

        data = dict(request.data)
        val_favorite = data["favorite"]
        image_hashes = data["image_hashes"]

        updated = []
        not_updated = []
        user = User.objects.get(username=request.user)

        for image_hash in image_hashes:
            try:
                photo = Photos.objects.get(image_hash=image_hash)
            except Photos.DoesNotExist:
                logger.warning(
                    "Could not set photo %s to favorite. It does not exist.", image_hash
                )

                continue

            if photo.owner == request.user:
                if val_favorite and photo.rating < user.favorite_min_rating:
                    photo.rating = user.favorite_min_rating
                    photo.save()
                    updated.append(PhotosSerializer(photo).data)
                elif not val_favorite and photo.rating >= user.favorite_min_rating:
                    photo.rating = 0
                    photo.save()
                    updated.append(PhotosSerializer(photo).data)
                else:
                    not_updated.append(PhotosSerializer(photo).data)
            else:
                not_updated.append(PhotosSerializer(photo).data)

        if val_favorite:
            logger.info(
                "%d photos were set favorite. %d photos were already in favorite.",
                len(updated),
                len(not_updated),
            )
        else:
            logger.info(
                "%d photos were removed from favorites. %d photos were already not in favorites.",
                len(updated),
                len(not_updated),
            )

        return Response(
            {
                "status": True,
                "results": updated,
                "updated": updated,
                "not_updated": not_updated,
            }
        )


class SetPhotosHidden(APIView):
    """Set photos hidden."""

    def post(self, request, format=None):
        """Handle the POST request to update the hidden status of photos based
        on the provided data."""

        data = dict(request.data)
        val_hidden = data["hidden"]
        image_hashes = data["image_hashes"]

        updated = []
        not_updated = []

        for image_hash in image_hashes:
            try:
                photo = Photos.objects.get(image_hash=image_hash)
            except Photos.DoesNotExist:
                logger.warning(
                    "Could not set photo %s to hidden. It does not exist.", image_hash
                )

                continue

            if photo.owner == request.user and photo.hidden != val_hidden:
                photo.hidden = val_hidden
                photo.save()
                updated.append(PhotosSerializer(photo).data)
            else:
                not_updated.append(PhotosSerializer(photo).data)

        if val_hidden:
            logger.info(
                "%d photos were set hidden. %d photos were already hidden.",
                len(updated),
                len(not_updated),
            )
        else:
            logger.info(
                "%d photos were set unhidden. %d photos were already unhidden.",
                len(updated),
                len(not_updated),
            )

        return Response(
            {
                "status": True,
                "results": updated,
                "updated": updated,
                "not_updated": not_updated,
            }
        )
