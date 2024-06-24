"""Album Thing view."""

import re

from django.db.models import Prefetch, Q
from rest_framework import filters, viewsets
from rest_framework.response import Response

from api.mixins.list_view_mixin import ListViewSet
from api.mixins.pagination_mixin import StandardResultsSetPagination
from api.models import AlbumThing
from api.models.photos import Photos
from api.models.user import User
from api.serializers.album_thing import (
    AlbumThingListSerializer,
    AlbumThingSerializer,
    GroupedThingPhotosSerializer,
)
from api.utils import logger


class AlbumThingViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumThingSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumThing.objects.none()
        return (
            AlbumThing.objects.filter(Q(owner=self.request.user))
            .filter(Q(photo_count__gt=0))
            .prefetch_related(
                Prefetch(
                    "photos",
                    queryset=Photos.visible.order_by("-exif_timestamp"),
                ),
                Prefetch(
                    "photos__owner",
                    queryset=User.objects.only(
                        "id", "username", "first_name", "last_name"
                    ),
                ),
            )
        )

    def retrieve(self, *args, **kwargs):
        queryset = self.get_queryset()
        logger.warning(args[0].__str__())
        albumid = re.findall(r"\'(.+?)\'", args[0].__str__())[0].split("/")[-2]
        serializer = GroupedThingPhotosSerializer(
            queryset.filter(id=albumid).first(), context={"request": self.request}
        )
        return Response({"results": serializer.data})

    def list(self, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = GroupedThingPhotosSerializer(
            queryset, many=True, context={"request": self.request}
        )
        return Response({"results": serializer.data})


class AlbumThingListViewSet(ListViewSet):
    serializer_class = AlbumThingListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ["title"]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumThing.objects.none()

        queryset = (
            AlbumThing.objects.filter(owner=self.request.user)
            .prefetch_related("cover_photos")
            .filter(photo_count__gt=0)
            .order_by("-title")
        )

        return queryset
