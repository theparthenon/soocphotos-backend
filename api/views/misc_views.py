# pylint: disable=no-member, redefined-builtin, unused-argument
"""Miscellaneous views that did not fit anywhere else."""

import os
from urllib.parse import quote
import subprocess
import magic

from django.conf import settings
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseForbidden,
    StreamingHttpResponse,
)
from django.db.models import Q
from django.utils.encoding import iri_to_uri

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from api.models import Photos, User


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
    permission_classes = (AllowAny,)

    def _get_protected_media_url(self, path, fname):
        return "/protected_media{}/{}".format(path, fname)

    def _generate_response(self, photo, path, fname, transcode_videos):
        if "thumbnail" in path:
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

        if path.lower() == "embedded_media":
            jwt = request.COOKIES.get("jwt")
            query = Q(public=True)

            if request.user.is_authenticated:
                query = Q(owner=request.user)

            if (
                jwt is not None
            ):  # pragma: no cover, currently it's difficult to test requests with jwt in cookies
                try:
                    token = AccessToken(jwt)
                    user = User.objects.filter(id=token["user_id"]).only("id").first()
                    query = Q(owner=user)
                except TokenError:
                    pass

            try:
                photo = Photos.objects.filter(query, image_hash=fname).first()

                if not photo or photo.original_image.embedded_media.count() < 1:
                    raise Photos.DoesNotExist()
            except Photos.DoesNotExist:
                return HttpResponse(status=404)

            response = HttpResponse()
            response["Content-Type"] = "video/mp4"
            response["X-Accel-Redirect"] = f"/protected_media/{path}/{fname}_1.mp4"

            return response

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

            if photo.owner == user:
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
                    "/original" + photo.original_image.path[len(settings.PHOTOS) :]
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
