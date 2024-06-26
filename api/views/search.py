from django.db.models import Prefetch, Q
from rest_framework.response import Response

from api.filters import SemanticSearchFilter
from api.mixins.list_view_mixin import ListViewSet
from api.mixins.pagination_mixin import HugeResultsSetPagination
from api.models import Photos, User
from api.serializers.photos import GroupedPhotosSerializer, PhotoSummarySerializer


class SearchListViewSet(ListViewSet):
    serializer_class = GroupedPhotosSerializer
    pagination_class = HugeResultsSetPagination
    filter_backends = (SemanticSearchFilter,)

    search_fields = [
        "search_captions",
        "search_location",
        "exif_timestamp",
    ]

    def get_queryset(self):
        return Photos.visible.filter(Q(owner=self.request.user)).order_by(
            "-exif_timestamp"
        )

    def list(self, request):
        queryset = self.filter_queryset(
            Photos.visible.filter(Q(owner=self.request.user))
            .prefetch_related(
                Prefetch(
                    "owner",
                    queryset=User.objects.only(
                        "id", "username", "first_name", "last_name"
                    ),
                ),
            )
            .only(
                "image_hash",
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
        serializer = PhotoSummarySerializer(queryset, many=True)
        return Response({"results": serializer.data})
