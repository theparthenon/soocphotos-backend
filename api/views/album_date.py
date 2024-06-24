"""Album Date view."""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, F, Prefetch, Q
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.mixins.list_view_mixin import ListViewSet
from api.mixins.pagination_mixin import RegularResultsSetPagination
from api.models import AlbumDate
from api.models.file import File
from api.models.user import User
from api.serializers.album_date import (
    AlbumDateSerializer,
    IncompleteAlbumDateSerializer,
)
from api.serializers.photos import PhotoSummarySerializer


class AlbumDateViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumDateSerializer
    pagination_class = RegularResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        photo_filter = []

        if not self.request.user.is_anonymous:
            photo_filter.append(Q(owner=self.request.user))

        if self.request.query_params.get("favorite"):
            min_rating = self.request.user.favorite_min_rating
            photo_filter.append(Q(rating__gte=min_rating))

        if self.request.query_params.get("hidden"):
            photo_filter.append(Q(hidden=True))
        else:
            photo_filter.append(Q(hidden=False))

        if self.request.query_params.get("video"):
            photo_filter.append(Q(video=True))

        if self.request.query_params.get("photo"):
            photo_filter.append(Q(video=False))

        if self.request.query_params.get("deleted"):
            photo_filter.append(Q(deleted=True))
        else:
            photo_filter.append(Q(deleted=False))

        if self.request.query_params.get("person"):
            photo_filter.append(
                Q(faces__person__id=self.request.query_params.get("person"))
            )
            photo_filter.append(
                Q(
                    faces__person_label_probability__gte=F(
                        "faces__photo__owner__confidence_person"
                    )
                )
            )

        album_date = AlbumDate.objects.filter(id=self.kwargs["pk"]).first()

        photo_qs = (
            album_date.photos.filter(*photo_filter)
            .prefetch_related(
                Prefetch(
                    "owner",
                    queryset=User.objects.only(
                        "id", "username", "first_name", "last_name"
                    ),
                ),
                Prefetch(
                    "original_image__embedded_media",
                    queryset=File.objects.only("hash"),
                ),
            )
            .order_by("-exif_timestamp")
            .only(
                "image_hash",
                "aspect_ratio",
                "video",
                "original_image",
                "search_location",
                "dominant_color",
                "rating",
                "hidden",
                "exif_timestamp",
                "owner",
                "video_length",
            )
        )

        # Paginate photo queryset
        page_size = self.request.query_params.get("size") or 100
        paginator = Paginator(photo_qs, page_size)
        page = self.request.query_params.get("page")

        try:
            photos = paginator.page(page)
        except PageNotAnInteger:
            photos = paginator.page(1)
        except EmptyPage:
            photos = paginator.page(paginator.num_pages)

        return album_date, photos, paginator.count

    def retrieve(self, *args, **kwargs):
        album_date, photos, count = self.get_queryset()
        serializer = AlbumDateSerializer(album_date, context={"request": self.request})
        serializer_data = serializer.data
        serializer_data["items"] = PhotoSummarySerializer(
            photos, many=True
        ).data  # Assuming you have a PhotoSerializer
        serializer_data["number_of_items"] = count

        return Response({"results": serializer_data})


# TODO: This could be the summary command in AlbumDateViewSet
class AlbumDateListViewSet(ListViewSet):
    serializer_class = IncompleteAlbumDateSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = [
        "photos__search_captions",
        "photos__search_location",
        "photos__faces__person__name",
    ]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        filter = []

        if self.request.query_params.get("hidden"):
            filter.append(Q(photos__hidden=True))
        else:
            filter.append(Q(photos__hidden=False))

        if self.request.query_params.get("deleted"):
            filter.append(Q(photos__deleted=True))
        else:
            filter.append(Q(photos__deleted=False))

        if not self.request.user.is_anonymous:
            filter.append(Q(owner=self.request.user))
            filter.append(Q(photos__owner=self.request.user))

        if self.request.query_params.get("favorite"):
            min_rating = self.request.user.favorite_min_rating
            filter.append(Q(photos__rating__gte=min_rating))

        if self.request.query_params.get("video"):
            filter.append(Q(photos__video=True))

        if self.request.query_params.get("photo"):
            filter.append(Q(photos__video=False))

        if self.request.query_params.get("person"):
            filter.append(
                Q(photos__faces__person__id=self.request.query_params.get("person"))
            )
            filter.append(
                Q(
                    photos__faces__person_label_probability__gte=F(
                        "photos__faces__photo__owner__confidence_person"
                    )
                )
            )

        qs = (
            AlbumDate.objects.filter(*filter)
            .annotate(photo_count=Count("photos", distinct=True))
            .filter(Q(photo_count__gt=0))
            .order_by(F("date").desc(nulls_last=True))
        )

        return qs

    def list(self, *args, **kwargs):
        serializer = IncompleteAlbumDateSerializer(self.get_queryset(), many=True)
        return Response({"results": serializer.data})
