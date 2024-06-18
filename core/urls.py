# pylint: disable=abstract-method, invalid-name
"""URL configuration for core project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, re_path
from rest_framework import permissions, routers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from api.views import misc_views, photos, upload


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer class to get a token pair for authentication."""

    @classmethod
    def get_token(cls, user):
        token = super(TokenObtainPairSerializer, cls).get_token(user)

        token["name"] = user.get_username()
        token["is_admin"] = user.is_superuser
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        token["confidence"] = user.confidence
        token["semantic_search_topk"] = user.semantic_search_topk

        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    """View class to get a token pair for authentication."""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.set_cookie("jwt", response.data["access"])
        response["Access-Control-Allow-Credentials"] = "true"
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """View class to refresh a token pair."""

    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.set_cookie("jwt", response.data["access"])
        response["Access-Control-Allow-Credentials"] = "true"
        return response


schema_view = get_schema_view(
    openapi.Info(
        title="SoocPhotos API",
        default_version="v1",
        description="Test description",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


router = routers.DefaultRouter()

router.register(
    r"api/photos/exists", upload.UploadPhotoExists, basename="photos_exists"
)

router.register(
    r"api/photos/recently-added",
    photos.RecentlyAddedPhotosViewSet,
    basename="photos_recently_added",
)

router.register(
    r"api/photos/without-timestamp",
    photos.PhotosWithoutTimestampViewSet,
    basename="photos_without_timestamp",
)


urlpatterns = [
    re_path(r"^", include(router.urls)),
    re_path(r"^api/django-admin/", admin.site.urls),
    re_path(r"^api/auth/token/obtain/$", CustomTokenObtainPairView.as_view()),
    re_path(r"^api/auth/token/refresh/$", CustomTokenRefreshView.as_view()),
    re_path(r"^api/upload/", upload.UploadPhotosChunked.as_view()),
    re_path(r"^api/upload/complete/", upload.UploadPhotosChunkedComplete.as_view()),
    re_path(
        r"^media/(?P<path>.*)/(?P<fname>.*)",
        misc_views.MediaAccessFullsizeOriginalView.as_view(),
        name="media",
    ),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^api/swagger<format>/",
            schema_view.without_ui(cache_timeout=0),
            name="schema-json",
        ),
        re_path(
            r"^api/swagger/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
        re_path(
            r"^api/redoc/",
            schema_view.with_ui("redoc", cache_timeout=0),
            name="schema-redoc",
        ),
    ]
