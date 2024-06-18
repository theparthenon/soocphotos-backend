# pylint: disable=no-member, redefined-builtin, unused-argument
"""Miscellaneous views that did not fit anywhere else."""

import os
from urllib.parse import quote
import subprocess
import magic

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseForbidden,
    StreamingHttpResponse,
)
from django.db.models import Q
from django.utils.encoding import iri_to_uri

from rest_framework.permissions import AllowAny
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
    """Controls access to protected media.

    Args:
        APIView (view): An APIView class.

    Returns:
        _type_: An HttpResponse class.
    """

    permission_classes = [AllowAny]

    def _get_protected_media_url(self, path, fname):
        return f"protected_media/{path}/{fname}"

    # @silk_profile(name='media')
    def get(self, request, path, fname, format=None):
        """
        Controls access to protected media.
        Args:
            request: Request object.
            path: Path to the media.
            fname: File name.
            format: Optional format parameter.
        Returns:
            An HttpResponse object.
        """

        jwt = request.COOKIES.get("jwt")

        # forbid access if trouble with jwt
        if jwt is not None:
            try:
                token = AccessToken(jwt)
            except TokenError:
                return HttpResponseForbidden()
        else:
            return HttpResponseForbidden()

        # grant access if the user is owner of the requested photo
        user = User.objects.filter(id=token["user_id"]).only("id").first()
        if Photos.owner == user:
            response = HttpResponse()
            response["Content-Type"] = "image/jpeg"
            response["X-Accel-Redirect"] = self._get_protected_media_url(path, fname)

            return response

        return HttpResponse(status=404)


class MediaAccessFullsizeOriginalView(APIView):
    """Controls access to protected media.

    Args:
        APIView (view): An APIView class.

    Raises:
        Photos.DoesNotExist: If the photo does not exist.
        Exception: If the photo is not owned by the user.

    Returns:
        _type_: An HttpResponse class.
    """

    permission_classes = (AllowAny,)

    def _get_protected_media_url(self, path, fname):
        return f"/protected_media{path}/{fname}"

    def _generate_response(self, photo, path, fname, transcode_videos):
        if "thumbnail" in path:
            response = HttpResponse()
            filename = os.path.splitext(Photos.thumbnail.path)[1]
            if "jpg" in filename:
                # handle non migrated systems
                response["Content-Type"] = "image/jpg"
                response["X-Accel-Redirect"] = Photos.optimized_image.path
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

        if Photos.video:
            # This is probably very slow -> Save the mime type when scanning
            mime = magic.Magic(mime=True)
            filename = mime.from_file(Photos.original_image.path)
            if transcode_videos:
                response = StreamingHttpResponse(
                    gen(VideoTranscoder(Photos.original_image.path)),
                    content_type="video/mp4",
                )
                return response
            else:
                response = HttpResponse()
                response["Content-Type"] = filename
                response["X-Accel-Redirect"] = iri_to_uri(
                    Photos.original_image.path.replace(settings.DATA_ROOT, "/original")
                )
                return response
        # faces and avatars
        response = HttpResponse()
        response["Content-Type"] = "image/jpg"
        response["X-Accel-Redirect"] = self._get_protected_media_url(path, fname)
        return response

    def get(self, request, path, fname, format=None):
        """
        Retrieves a resource based on the provided path and file name.
        Args:
            request (HttpRequest): The HTTP request object.
            path (str): The path of the resource.
            fname (str): The file name of the resource.
            format (str, optional): The format of the resource. Defaults to None.
        Returns:
            HttpResponse: The HTTP response object containing the requested resource.
        Raises:
            HttpResponseForbidden: If the user is not authenticated or the JWT token is
            invalid.
            HttpResponse: If the requested resource does not exist or the user does not
            have permission to access it.
        Notes:
            - If the path is "zip", the function checks if the user is authenticated and
              retrieves the corresponding zip file.
            - If the path is "avatars", the function checks if the user is authenticated and
              retrieves the corresponding avatar image.
            - If the path is "embedded_media", the function checks if the user is authenticated
              and retrieves the corresponding embedded media.
            - If the path is not "photos", the function checks if the user is authenticated and
              retrieves the corresponding resource.
            - If the path is "photos", the function checks if the user is authenticated and
              retrieves the corresponding original image.
        """

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
            except PermissionDenied:
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
            except ObjectDoesNotExist:
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
                if not photo:
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
            # or the photo is shared with the user
            image_hash = fname.split(".")[0].split("_")[0]  # janky alert
            user = (
                User.objects.filter(id=token["user_id"])
                .only("id", "transcode_videos")
                .first()
            )
            if Photos.owner == user:
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

            if Photos.original_image.path.startswith(settings.PHOTOS):
                internal_path = (
                    "/original" + Photos.original_image.path[len(settings.PHOTOS) :]
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
            # or the photo is shared with the user
            image_hash = fname.split(".")[0].split("_")[0]  # janky alert
            user = User.objects.filter(id=token["user_id"]).only("id").first()

            if internal_path is not None:
                response = HttpResponse()
                mime = magic.Magic(mime=True)
                filename = mime.from_file(Photos.original_image.path)
                response["Content-Type"] = filename
                response["Content-Disposition"] = (
                    f'inline; filename="{Photos.original_image.path.split("/")[-1]}"'
                )
                response["X-Accel-Redirect"] = internal_path
            else:
                try:
                    response = FileResponse(open(Photos.original_image.path, "rb"))
                except FileNotFoundError:
                    return HttpResponse(status=404)
                except PermissionError:
                    return HttpResponse(status=403)
                except IOError:
                    return HttpResponse(status=500)
                except Exception as exc:
                    raise Exception(  # pylint: disable=broad-exception-raised
                        f"Could not generate response from original image: {exc}"
                    ) from exc

            if Photos.owner == user:
                return response

            return HttpResponse(status=404)
