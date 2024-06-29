"""Person view."""

import re

from django.db.models import Count, Prefetch, Q
from rest_framework import filters, viewsets
from rest_framework.response import Response

from api.mixins.pagination_mixin import StandardResultsSetPagination
from api.models import Person, Photos
from api.models.face import Face
from api.serializers.person import GroupedPersonPhotosSerializer, PersonSerializer
from api.utils import logger


class AlbumPersonViewSet(viewsets.ModelViewSet):
    serializer_class = GroupedPersonPhotosSerializer

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return Person.objects.none()

        return (
            Person.objects.annotate(
                photo_count=Count(
                    "faces", filter=Q(faces__photo__hidden=False), distinct=True
                )
            )
            .filter(Q(photo_count__gt=0))
            .prefetch_related(
                Prefetch(
                    "faces",
                    queryset=Face.objects.filter(Q(person_label_is_inferred=False)),
                )
            )
            .prefetch_related(
                Prefetch(
                    "faces__photo",
                    queryset=Photos.objects.filter(
                        Q(faces__photo__hidden=False) & Q(owner=self.request.user)
                    )
                    .distinct()
                    .order_by("-exif_timestamp")
                    .only("image_hash", "exif_timestamp", "rating", "hidden"),
                )
            )
        )

    def retrieve(self, *args, **kwargs):
        queryset = self.get_queryset()
        logger.warning(args[0].__str__())

        album_id = re.findall(r"\'(.+?)\'", args[0].__str__())[0].split("/")[-2]
        serializer = GroupedPersonPhotosSerializer(
            queryset.filter(id=album_id).first(), context={"request": self.request}
        )
        return Response({"results": serializer.data})

    def list(self, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = GroupedPersonPhotosSerializer(
            queryset, many=True, context={"request": self.request}
        )
        return Response({"results": serializer.data})


class PersonViewSet(viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ["name"]
    ordering_fields = ["name"]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return Person.objects.none()
        qs = (
            Person.objects.filter(
                ~Q(kind=Person.KIND_CLUSTER)
                & ~Q(kind=Person.KIND_UNKNOWN)
                & Q(cluster_owner=self.request.user)
            )
            .select_related("cover_photo", "cover_face")
            .only(
                "name",
                "face_count",
                "id",
                "cover_face",
                "cover_photo",
            )
        )

        return qs
