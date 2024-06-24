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

from api.views import (
    album_date,
    album_place,
    album_thing,
    faces,
    misc_views,
    person,
    photos,
    upload,
    user,
)


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

router.register(r"api/albums/date", album_date.AlbumDateViewSet, basename="album_date")

router.register(
    r"api/albums/date/list", album_date.AlbumDateListViewSet, basename="album_date_list"
)

router.register(
    r"api/albums/people", person.AlbumPersonViewSet, basename="album_people"
)

router.register(
    r"api/albums/place", album_place.AlbumPlaceViewSet, basename="album_place"
)

router.register(
    r"api/albums/place/list",
    album_place.AlbumPlaceListViewSet,
    basename="album_place_list",
)

router.register(
    r"api/albums/thing", album_thing.AlbumThingViewSet, basename="album_thing"
)

router.register(
    r"api/albums/thing/list",
    album_thing.AlbumThingListViewSet,
    basename="album_thing_list",
)

router.register(r"api/faces", faces.FaceListView, basename="faces")

router.register(
    r"api/faces/incomplete", faces.FaceIncompleteListView, basename="faces_incomplete"
)

router.register(r"api/people", person.PersonViewSet, basename="people")

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

router.register(r"api/user", user.UserViewSet, basename="user")
router.register(r"api/user/manage", user.ManageUserViewSet, basename="user_manage")
router.register(r"api/user/delete", user.DeleteUserViewSet, basename="user_delete")


urlpatterns = [
    re_path(r"^", include(router.urls)),
    re_path(r"^api/django-admin/", admin.site.urls),
    re_path(r"^api/auth/token/obtain/$", CustomTokenObtainPairView.as_view()),
    re_path(r"^api/auth/token/refresh/$", CustomTokenRefreshView.as_view()),
    re_path(
        r"^api/faces/label/", faces.SetFacePersonLabel.as_view(), name="faces_label"
    ),
    re_path(r"^api/faces/delete/", faces.DeleteFaces.as_view(), name="faces_delete"),
    re_path(r"^api/faces/scan/", faces.ScanFacesView.as_view(), name="faces_scan"),
    re_path(r"^api/faces/train/", faces.TrainFaceView.as_view(), name="faces_train"),
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
