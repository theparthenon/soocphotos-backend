"""Albums views."""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from api.mixins.list_view_mixin import ListViewSet
from api.mixins.pagination_mixin import StandardResultsSetPagination
from api.models import Albums
from api.serializers.albums import (
    AlbumSerializer,
    AlbumListSerializer
)


class AlbumViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        return AlbumSerializer

    def list(self, *args, **kwargs):
        if self.request.user.is_anonymous:
            return Albums.objects.none()

        queryset = (
            Albums.objects.order_by("title")
            .annotate(
                photo_count=Count(
                    "photos", filter=Q(photos__hidden=False),
                    distinct=True
                )
            )
            .order_by("title")
        )
        serializer = AlbumListSerializer(queryset, many=True)

        return Response({"results": serializer.data})

    def retrieve(self, request, pk=None):
        queryset = Albums.objects.all()
        album = get_object_or_404(queryset, pk=pk)
        serializer = AlbumSerializer(album)

        return Response({"results": serializer.data})