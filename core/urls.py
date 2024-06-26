# pylint: disable=abstract-method, invalid-name
"""URL configuration for core project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, re_path
from rest_framework import permissions, routers
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from api.views import (
    authentication,
    album_date,
    album_place,
    album_thing,
    dataviz,
    faces,
    jobs,
    misc_views,
    person,
    photos,
    search,
    services,
    upload,
    user,
)


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

router.register(r"api/jobs", jobs.JobViewSet, basename="jobs")

router.register(r"api/people", person.PersonViewSet, basename="people")

router.register(r"api/photos", photos.PhotosViewSet, basename="photos")

router.register(r"api/photos/edit", photos.PhotoEditViewSet, basename="photos_edit")

router.register(
    r"api/photos/exists", upload.UploadPhotoExists, basename="photos_exists"
)

router.register(
    r"api/photos/recently-added",
    photos.RecentlyAddedPhotosViewSet,
    basename="photos_recently_added",
)

router.register(
    r"api/photos/search-list", search.SearchListViewSet, basename="photos_search"
)

router.register(
    r"api/photos/without-timestamp",
    photos.PhotosWithoutTimestampViewSet,
    basename="photos_without_timestamp",
)

router.register(r"api/services", services.ServiceViewSet, basename="services")

router.register(r"api/user", user.UserViewSet, basename="user")

router.register(r"api/user/manage", user.ManageUserViewSet, basename="user_manage")

router.register(r"api/user/delete", user.DeleteUserViewSet, basename="user_delete")


urlpatterns = [
    re_path(r"^", include(router.urls)),
    re_path(r"^api/django-admin/", admin.site.urls),
    re_path(
        r"^api/auth/token/obtain/$", authentication.CustomTokenObtainPairView.as_view()
    ),
    re_path(
        r"^api/auth/token/refresh/$", authentication.CustomTokenRefreshView.as_view()
    ),
    re_path(
        r"^api/delete/zip/(?P<fname>.*)",
        misc_views.DeleteZipView.as_view(),
        name="delete-zip",
    ),
    re_path(r"^api/faces/cluster", faces.ClusterFaceView.as_view()),
    re_path(r"^api/faces/delete", faces.DeleteFaces.as_view(), name="faces_delete"),
    re_path(
        r"^api/faces/label", faces.SetFacePersonLabel.as_view(), name="faces_label"
    ),
    re_path(r"^api/faces/scan", faces.ScanFacesView.as_view(), name="faces_scan"),
    re_path(r"^api/faces/train", faces.TrainFaceView.as_view(), name="faces_train"),
    re_path(r"^api/location/sunburst", dataviz.LocationSunburst.as_view()),
    re_path(r"^api/location/timeline", dataviz.LocationTimeline.as_view()),
    re_path(r"^api/photos/download$", misc_views.ZipListPhotosView_V2.as_view()),
    re_path(r"^api/photos/edit/delete", photos.DeletePhotos.as_view()),
    re_path(
        r"^api/photos/edit/delete/duplicates", photos.DeleteDuplicatePhotos.as_view()
    ),
    re_path(
        r"^api/photos/edit/delete/missing", misc_views.DeleteMissingPhotosView.as_view()
    ),
    re_path(r"^api/photos/edit/favorite", photos.SetPhotosFavorite.as_view()),
    re_path(r"^api/photos/edit/hide", photos.SetPhotosHidden.as_view()),
    re_path(
        r"^api/photos/edit/caption/generate", photos.GeneratePhotoCaption.as_view()
    ),
    re_path(r"^api/photos/edit/caption/save", photos.SavePhotoCaption.as_view()),
    re_path(r"^api/photos/edit/set-deleted", photos.SetPhotosDeleted.as_view()),
    re_path(r"^api/photos/month-counts", dataviz.PhotoMonthCountsView.as_view()),
    re_path(r"^api/rq-available/$", jobs.QueueAvailabilityView.as_view()),
    # re_path(r"^api/settings/site", misc_views.SiteSettingsView.as_view()),
    re_path(r"^api/scan/photos", misc_views.ScanPhotosView.as_view()),
    re_path(r"^api/scan/photos/uploaded", misc_views.FullScanPhotosView.as_view()),
    re_path(r"^api/scan/photos/full", misc_views.FullScanPhotosView.as_view()),
    re_path(r"^api/search-term-examples", misc_views.SearchTermExamples.as_view()),
    re_path(r"^api/stats", dataviz.StatsView.as_view()),
    re_path(r"^api/stats/server", dataviz.ServerStatsView.as_view()),
    re_path(r"^api/stats/storage", misc_views.StorageStatsView.as_view()),
    re_path(r"^api/upload/", upload.UploadPhotosChunked.as_view()),
    re_path(r"^api/upload/complete/", upload.UploadPhotosChunkedComplete.as_view()),
    re_path(r"^api/word-cloud", dataviz.SearchTermWordCloudView.as_view()),
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
