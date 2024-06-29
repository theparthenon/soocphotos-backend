# pylint: disable=no-member, redefined-builtin, unused-argument
"""Miscellaneous views that did not fit anywhere else."""

import os
from urllib.parse import quote
import subprocess
from api.utils_api import get_search_term_examples
import magic
import uuid
import jsonschema

from constance import config as site_config
from django.conf import settings
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseForbidden,
    StreamingHttpResponse,
)
from django.db.models import Sum, Q
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django_q.tasks import AsyncTask, Chain

from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from api.all_tasks import create_download_job, delete_missing_photos, delete_zip_file
from api.directory_watcher import scan_photos
from api.ml_models import do_all_models_exist, download_models
from api.models import Job, Photos, User
from api.schemas.site_settings import site_settings_schema
from api.utils import logger


class SiteSettingsView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = (AllowAny,)
        else:
            self.permission_classes = (IsAdminUser,)

        return super(SiteSettingsView, self).get_permissions()

    def get(self, request, format=None):
        out = {}
        out["allow_registration"] = site_config.ALLOW_REGISTRATION
        out["allow_upload"] = site_config.ALLOW_UPLOAD
        out["skip_patterns"] = site_config.SKIP_PATTERNS
        out["heavyweight_process"] = site_config.HEAVYWEIGHT_PROCESS
        out["map_api_provider"] = site_config.MAP_API_PROVIDER
        out["map_api_key"] = site_config.MAP_API_KEY
        out["captioning_model"] = site_config.CAPTIONING_MODEL
        out["llm_model"] = site_config.LLM_MODEL
        return Response(out)

    def post(self, request, format=None):
        jsonschema.validate(request.data, site_settings_schema)
        if "allow_registration" in request.data.keys():
            site_config.ALLOW_REGISTRATION = request.data["allow_registration"]
        if "allow_upload" in request.data.keys():
            site_config.ALLOW_UPLOAD = request.data["allow_upload"]
        if "skip_patterns" in request.data.keys():
            site_config.SKIP_PATTERNS = request.data["skip_patterns"]
        if "heavyweight_process" in request.data.keys():
            site_config.HEAVYWEIGHT_PROCESS = request.data["heavyweight_process"]
        if "map_api_provider" in request.data.keys():
            site_config.MAP_API_PROVIDER = request.data["map_api_provider"]
        if "map_api_key" in request.data.keys():
            site_config.MAP_API_KEY = request.data["map_api_key"]
        if "captioning_model" in request.data.keys():
            site_config.CAPTIONING_MODEL = request.data["captioning_model"]
        if "llm_model" in request.data.keys():
            site_config.LLM_MODEL = request.data["llm_model"]
        if not do_all_models_exist():
            AsyncTask(download_models, User.objects.get(id=request.user)).run()

        return self.get(request, format=format)


class VideoTranscoder:
    """Transcodes a video into a smaller format."""

    process = ""

    def __init__(self, path):
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            path,
            "-vcodec",
            "libx264",
            "-preset",
            "ultrafast",
            "-movflags",
            "frag_keyframe+empty_moov",
            "-filter:v",
            ("scale=-2:" + str(720)),
            "-f",
            "mp4",
            "-",
        ]
        self.process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def __del__(self):
        self.process.kill()


def gen(transcoder):
    """
    Generator function that yields the output of a transcoding process.
    Args:
        transcoder (Transcoder): An instance of the Transcoder class.
    Yields:
        bytes: A byte string containing the output of the transcoding process.
    """

    for resp in iter(transcoder.process.stdout.readline, b""):
        yield resp


class MediaAccessView(APIView):
    permission_classes = (AllowAny,)

    def _get_protected_media_url(self, path, fname):
        return "protected_media/{}/{}".format(path, fname)

    # @silk_profile(name='media')
    def get(self, request, path, fname, format=None):
        jwt = request.COOKIES.get("jwt")
        image_hash = fname.split(".")[0].split("_")[0]

        try:
            photo = Photos.objects.get(image_hash=image_hash)
        except Photos.DoesNotExist:
            return HttpResponse(status=404)

        # forbid access if trouble with jwt
        if jwt is not None:
            try:
                token = AccessToken(jwt)
            except TokenError:
                return HttpResponseForbidden()
        else:
            return HttpResponseForbidden()

        # grant access if the user is owner of the requested photo
        image_hash = fname.split(".")[0].split("_")[0]  # janky alert
        user = User.objects.filter(id=token["user_id"]).only("id").first()

        if photo.owner == user:
            response = HttpResponse()
            response["Content-Type"] = "image/jpeg"
            response["X-Accel-Redirect"] = self._get_protected_media_url(path, fname)

            return response

        return HttpResponse(status=404)


class MediaAccessFullsizeOriginalView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_protected_media_url(self, path, fname):
        return "/protected_media{}/{}".format(path, fname)

    def _generate_response(self, photo, path, fname, transcode_videos):
        if "thumbnail" in path:
            logger.info("path: %s", path)
            logger.info("Photo: %s", photo)
            response = HttpResponse()
            filename = os.path.splitext(photo.thumbnail.path)[1]

            if "webp" in filename:
                response["Content-Type"] = "image/webp"
                response["X-Accel-Redirect"] = self._get_protected_media_url(
                    path, fname + ".webp"
                )

            if "mp4" in filename:
                response["Content-Type"] = "video/mp4"
                response["X-Accel-Redirect"] = self._get_protected_media_url(
                    path, fname + ".mp4"
                )

            return response

        if "faces" in path:
            response = HttpResponse()
            response["Content-Type"] = "image/jpg"
            response["X-Accel-Redirect"] = self._get_protected_media_url(path, fname)

            return response

        if photo.video:
            # This is probably very slow -> Save the mime type when scanning
            mime = magic.Magic(mime=True)
            filename = mime.from_file(photo.original_image.path)

            if transcode_videos:
                response = StreamingHttpResponse(
                    gen(VideoTranscoder(photo.original_image.path)),
                    content_type="video/mp4",
                )

                return response

            response = HttpResponse()
            response["Content-Type"] = filename
            response["X-Accel-Redirect"] = iri_to_uri(
                photo.original_image.path.replace(settings.DATA_ROOT, "/original")
            )

            return response

        # faces and avatars
        response = HttpResponse()
        response["Content-Type"] = "image/jpg"
        response["X-Accel-Redirect"] = self._get_protected_media_url(path, fname)

        return response

    # @extend_schema(
    #     description="Endpoint to load media files.",
    #     parameters=[
    #         OpenApiParameter(
    #             name="path",
    #             description="Kind of media file you want to load",
    #             required=True,
    #             type=OpenApiTypes.STR,
    #             enum=[
    #                 "thumbnails_big",
    #                 "square_thumbnails",
    #                 "small_square_thumbnails",
    #                 "avatars",
    #                 "photos",
    #                 "faces",
    #                 "embedded_media",
    #             ],
    #             location=OpenApiParameter.PATH,
    #         ),
    #         OpenApiParameter(
    #             name="fname",
    #             description="Usually the hash of the file. Faces have the format <hash>_<face_id>.jpg and avatars <first_name>avatar_<hash>.png",
    #             required=True,
    #             type=OpenApiTypes.STR,
    #             location=OpenApiParameter.PATH,
    #         ),
    #     ],
    # )
    def get(self, request, path, fname, format=None):
        if path.lower() == "zip":
            jwt = request.COOKIES.get("jwt")

            if jwt is not None:
                try:
                    token = AccessToken(jwt)
                except TokenError:
                    return HttpResponseForbidden()
            else:
                return HttpResponseForbidden()

            try:
                filename = fname + str(token["user_id"]) + ".zip"
                response = HttpResponse()
                response["Content-Type"] = "application/x-zip-compressed"
                response["X-Accel-Redirect"] = self._get_protected_media_url(
                    path, filename
                )

                return response
            except Exception:
                return HttpResponseForbidden()

        if path.lower() == "avatars":
            jwt = request.COOKIES.get("jwt")

            if jwt is not None:
                try:
                    token = AccessToken(jwt)
                except TokenError:
                    return HttpResponseForbidden()
            else:
                return HttpResponseForbidden()

            try:
                user = User.objects.filter(id=token["user_id"]).only("id").first()
                response = HttpResponse()
                response["Content-Type"] = "image/png"
                response["X-Accel-Redirect"] = "/protected_media/" + path + "/" + fname

                return response
            except Exception:
                return HttpResponse(status=404)

        if path.lower() != "photos":
            jwt = request.COOKIES.get("jwt")
            image_hash = fname.split(".")[0].split("_")[0]

            try:
                photo = Photos.objects.get(image_hash=image_hash)
            except Photos.DoesNotExist:
                return HttpResponse(status=404)

            # forbid access if trouble with jwt
            if jwt is not None:
                try:
                    token = AccessToken(jwt)
                except TokenError:
                    return HttpResponseForbidden()
            else:
                return HttpResponseForbidden()

            # grant access if the user is owner of the requested photo
            image_hash = fname.split(".")[0].split("_")[0]  # janky alert
            user = (
                User.objects.filter(id=token["user_id"])
                .only("id", "transcode_videos")
                .first()
            )

            if IsAuthenticated():
                return self._generate_response(
                    photo, path, fname, user.transcode_videos
                )

            return HttpResponse(status=404)
        else:
            jwt = request.COOKIES.get("jwt")
            image_hash = fname.split(".")[0].split("_")[0]

            try:
                photo = Photos.objects.get(image_hash=image_hash)
            except Photos.DoesNotExist:
                return HttpResponse(status=404)

            if photo.original_image.path.startswith(settings.PHOTOS):
                internal_path = (
                    "/originals" + photo.original_image.path[len(settings.PHOTOS) :]
                )
            else:
                # If, for some reason, the file is in a weird place, handle that.
                internal_path = None

            internal_path = quote(internal_path)

            # forbid access if trouble with jwt
            if jwt is not None:
                try:
                    token = AccessToken(jwt)
                except TokenError:
                    return HttpResponseForbidden()
            else:
                return HttpResponseForbidden()

            # grant access if the user is owner of the requested photo
            image_hash = fname.split(".")[0].split("_")[0]  # janky alert
            user = User.objects.filter(id=token["user_id"]).only("id").first()

            if internal_path is not None:
                response = HttpResponse()
                mime = magic.Magic(mime=True)
                filename = mime.from_file(photo.original_image.path)
                response["Content-Type"] = filename
                response["Content-Disposition"] = 'inline; filename="{}"'.format(
                    photo.original_image.path.split("/")[-1]
                )
                response["X-Accel-Redirect"] = internal_path
            else:
                try:
                    response = FileResponse(open(photo.original_image.path, "rb"))
                except FileNotFoundError:
                    return HttpResponse(status=404)
                except PermissionError:
                    return HttpResponse(status=403)
                except IOError:
                    return HttpResponse(status=500)
                except Exception:
                    raise

            if photo.owner == user:
                return response

            return HttpResponse(status=404)


class StorageStatsView(APIView):
    def get(self, request, format=None):
        import shutil

        total_storage, used_storage, free_storage = shutil.disk_usage(
            settings.DATA_ROOT
        )
        return Response(
            {
                "total_storage": total_storage,
                "used_storage": used_storage,
                "free_storage": free_storage,
            }
        )


class ImageTagView(APIView):
    @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request, format=None):
        # Add an exception for the directory '/code'
        subprocess.run(
            ["git", "config", "--global", "--add", "safe.directory", "/code"]
        )

        # Get the current commit hash
        git_hash = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .strip()
            .decode("utf-8")
        )
        return Response(
            {"image_tag": os.environ.get("IMAGE_TAG", ""), "git_hash": git_hash}
        )


class SearchTermExamples(APIView):
    @method_decorator(vary_on_cookie)
    @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request, format=None):
        search_term_examples = get_search_term_examples(request.user)
        return Response({"results": search_term_examples})


class ScanPhotosView(APIView):
    def post(self, request, format=None):
        return self._scan_photos(request)

    # Deprecated
    def get(self, request, format=None):
        return self._scan_photos(request)

    def _scan_photos(self, request):
        chain = Chain()
        if not do_all_models_exist():
            chain.append(download_models, request.user)
        try:
            job_id = uuid.uuid4()
            chain.append(
                scan_photos, request.user, False, job_id, request.user.scan_directory
            )
            chain.run()
            return Response({"status": True, "job_id": job_id})
        except BaseException:
            logger.exception("An Error occurred")
            return Response({"status": False})


class FullScanPhotosView(APIView):
    def post(self, request, format=None):
        return self._scan_photos(request)

    def get(self, request, format=None):
        return self._scan_photos(request)

    def _scan_photos(self, request):
        chain = Chain()

        if not do_all_models_exist():
            chain.append(download_models, request.user)

        try:
            job_id = uuid.uuid4()
            chain.append(
                scan_photos, request.user, True, job_id, request.user.scan_directory
            )
            chain.run()

            return Response({"status": True, "job_id": job_id})

        except BaseException as e:
            logger.exception("An Error occurred: %s", e)

            return Response({"status": False})


class DeleteMissingPhotosView(APIView):
    def post(self, request, format=None):
        return self._delete_missing_photos(request, format)

    def get(self, request, format=None):
        return self._delete_missing_photos(request, format)

    def _delete_missing_photos(self, request, format=None):
        try:
            job_id = uuid.uuid4()
            delete_missing_photos(request.user, job_id)

            return Response({"status": True, "job_id": job_id})
        except BaseException:
            logger.exception("An Error occurred")

            return Response({"status": False})


class ZipListPhotosView_V2(APIView):
    def post(self, request):
        import shutil

        free_storage = shutil.disk_usage("/").free
        data = dict(request.data)

        if "image_hashes" not in data:
            return

        photo_query = Photos.objects.filter(owner=self.request.user)
        # Filter photos based on image hashes
        photos = photo_query.filter(image_hash__in=data["image_hashes"])

        if not photos.exists():
            return

        # Calculate the total file size using aggregate
        total_file_size = photos.aggregate(Sum("size"))["size__sum"] or 0
        if free_storage < total_file_size:
            return Response(data={"status": "Insufficient Storage"}, status=507)

        file_uuid = uuid.uuid4()
        filename = str(str(file_uuid) + str(self.request.user.id) + ".zip")

        job_id = create_download_job(
            Job.JOB_DOWNLOAD_PHOTOS,
            user=self.request.user,
            photos=list(photos),
            filename=filename,
        )
        response = {"job_id": job_id, "url": file_uuid}

        return Response(data=response, status=200)

    def get(self, request):
        job_id = request.GET["job_id"]
        print(job_id)

        if job_id is None:
            return Response(status=404)

        try:
            job = Job.objects.get(job_id=job_id)

            if job.finished:
                return Response(data={"status": "SUCCESS"}, status=200)
            elif job.failed:
                return Response(
                    data={"status": "FAILURE", "result": job.result}, status=500
                )
            else:
                return Response(
                    data={"status": "PENDING", "progress": job.result}, status=202
                )
        except BaseException as e:
            logger.error(str(e))

            return Response(status=404)


class DeleteZipView(APIView):
    def delete(self, request, fname):
        jwt = request.COOKIES.get("jwt")

        if jwt is not None:
            try:
                token = AccessToken(jwt)
            except TokenError:
                return HttpResponseForbidden()
        else:
            return HttpResponseForbidden()

        filename = fname + str(token["user_id"]) + ".zip"

        try:
            delete_zip_file(filename)

            return Response(status=200)
        except BaseException as e:
            logger.error(str(e))

            return Response(status=404)
