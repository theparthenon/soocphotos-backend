"""Album Place view."""

import re

from django.db.models import Count, Prefetch, Q
from rest_framework import filters, viewsets
from rest_framework.response import Response

from api.mixins.pagination_mixin import StandardResultsSetPagination
from api.models import AlbumPlace
from api.models.photos import Photos
from api.serializers.album_place import (
    AlbumPlaceListSerializer,
    AlbumPlaceSerializer,
    GroupedPlacePhotosSerializer,
)
from api.utils import logger


class AlbumPlaceViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumPlaceSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ["title"]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumPlace.objects.none()

        return (
            AlbumPlace.objects.annotate(
                photo_count=Count(
                    "photos", filter=Q(photos__hidden=False), distinct=True
                )
            )
            .filter(Q(photo_count__gt=0) & Q(owner=self.request.user))
            .prefetch_related(
                Prefetch(
                    "photos",
                    queryset=Photos.objects.filter(hidden=False)
                    .only("image_hash", "rating", "hidden", "exif_timestamp")
                    .order_by("-exif_timestamp"),
                )
            )
        )

    def get_list_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumPlace.objects.none()

        cover_photos_query = Photos.objects.filter(hidden=False).only(
            "image_hash", "video"
        )

        return (
            AlbumPlace.objects.filter(owner=self.request.user)
            .annotate(
                photo_count=Count(
                    "photos", filter=Q(photos__hidden=False), distinct=True
                )
            )
            .prefetch_related(
                Prefetch(
                    "photos", queryset=cover_photos_query[:4], to_attr="cover_photos"
                )
            )
            .filter(Q(photo_count__gt=0) & Q(owner=self.request.user))
            .order_by("title")
        )


    def list(self, *args, **kwargs):
        serializer = AlbumPlaceListSerializer(self.get_list_queryset(), many=True)

        return Response({"results": serializer.data})

    def retrieve(self, *args, **kwargs):
        queryset = self.get_queryset()
        logger.warning(str(args[0]))

        album_id = re.findall(r"\'(.+?)\'", str(args[0]))[0].split("/")[-2]
        serializer = GroupedPlacePhotosSerializer(
            queryset.filter(id=album_id).first(), context={"request": self.request}
        )

        return Response({"result": serializer.data})


# class AlbumPlaceListViewSet(viewsets.ModelViewSet):
#     serializer_class = AlbumPlaceListSerializer
#     pagination_class = StandardResultsSetPagination
#     filter_backends = (filters.SearchFilter,)
#     search_fields = ["title"]

#     def get_queryset(self):
#         if self.request.user.is_anonymous:
#             return AlbumPlace.objects.none()

#         cover_photos_query = Photos.objects.filter(hidden=False).only(
#             "image_hash", "video"
#         )

#         return (
#             AlbumPlace.objects.filter(owner=self.request.user)
#             .annotate(
#                 photo_count=Count(
#                     "photos", filter=Q(photos__hidden=False), distinct=True
#                 )
#             )
#             .prefetch_related(
#                 Prefetch(
#                     "photos", queryset=cover_photos_query[:4], to_attr="cover_photos"
#                 )
#             )
#             .filter(Q(photo_count__gt=0) & Q(owner=self.request.user))
#             .order_by("title")
#         )
