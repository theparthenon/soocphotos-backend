from django.db.models import Count, Q
from rest_framework import filters, viewsets

from api.mixins.list_view_mixin import ListViewSet
from api.mixins.pagination_mixin import StandardResultsSetPagination
from api.models import AlbumUser
from api.serializers.album_user import (
    AlbumUserEditSerializer,
    AlbumUserListSerializer,
    AlbumUserSerializer,
)


class AlbumUserViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumUserSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumUser.objects.none()

        qs = (
            AlbumUser.objects.filter(
                Q(owner=self.request.user) | Q(shared_to__exact=self.request.user.id)
            )
            .distinct("id")
            .order_by("-id")
        )

        return qs


# To-Do: Could be the list command in AlbumUserViewSet
class AlbumUserListViewSet(ListViewSet):
    serializer_class = AlbumUserListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ["title"]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumUser.objects.none()

        return (
            AlbumUser.objects.filter(owner=self.request.user)
            .annotate(
                photo_count=Count(
                    "photos", filter=Q(photos__hidden=False), distinct=True
                )
            )
            .filter(Q(photo_count__gt=0) & Q(owner=self.request.user))
            .order_by("title")
        )


class AlbumUserEditViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumUserEditSerializer
    pagination_class = StandardResultsSetPagination

    def retrieve(self, *args, **kwargs):
        return super(AlbumUserEditViewSet, self).retrieve(*args, **kwargs)

    def list(self, *args, **kwargs):
        return super(AlbumUserEditViewSet, self).list(*args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return AlbumUser.objects.none()

        return AlbumUser.objects.filter(owner=self.request.user).order_by("title")
