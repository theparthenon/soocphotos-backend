"""Chunked upload viewset."""

import io
import os
import pathvalidate as pv

from chunked_upload.constants import http_status
from chunked_upload.exceptions import ChunkedUploadError
from chunked_upload.models import ChunkedUpload
from chunked_upload.views import ChunkedUploadCompleteView, ChunkedUploadView
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_q.tasks import AsyncTask
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from api.directory_watcher import create_new_image, handle_new_image
from api.models import Photos, User
from api.utils import calculate_hash, calculate_hash_b64, logger


class UploadPhotoExists(viewsets.ViewSet):
    """Checks if a photo already exists."""

    def retrieve(self, request, pk):
        """Only allow GET requests."""

        try:
            Photos.objects.get(image_hash=pk)

            return Response({"exists": True})
        except Photos.DoesNotExist:
            return Response({"exists": False})


@method_decorator(csrf_exempt, name="dispatch")
class UploadPhotosChunked(ChunkedUploadView):
    """Upload chunked segments of a photo."""

    model = ChunkedUpload

    def check_permissions(self, request):
        if not settings.ALLOW_UPLOAD:
            logger.info("Uploads are not allowed.")

            return HttpResponseForbidden()

        jwt = request.COOKIES.get("jwt")

        if jwt is not None:
            try:
                AccessToken(jwt)
            except TokenError as e:
                logger.info("Error with JWT token: %s", e)

                return HttpResponseForbidden()
        else:
            logger.info("No JWT token found.")

            return HttpResponseForbidden()
        # TODO: make deactivatable
        # TODO: Check if file is allowed type (should use is_photo from utils)
        user = User.objects.filter(id=request.POST.get("user")).first()

        if not user or not user.is_authenticated:
            raise ChunkedUploadError(
                status=http_status.HTTP_403_FORBIDDEN,
                detail="Authentication credentials were not provided.",
            )

    def create_chunked_upload(self, save=False, **attrs):
        """
        Creates new chunked upload instance. Called if no 'upload_id' is found in the POST data.
        """

        chunked_upload = self.model(**attrs)
        # File starts empty
        chunked_upload.file.save(  # pylint: disable=no-member
            name="tmp", content=ContentFile(""), save=save
        )

        return chunked_upload


@method_decorator(csrf_exempt, name="dispatch")
class UploadPhotosChunkedComplete(ChunkedUploadCompleteView):
    """What to do when uploaded photo is complete."""

    model = ChunkedUpload

    def check_permissions(self, request):
        if not settings.ALLOW_UPLOAD:
            logger.info("Uploads are not allowed.")

            return HttpResponseForbidden()

        jwt = request.COOKIES.get("jwt")

        if jwt is not None:
            try:
                AccessToken(jwt)
            except TokenError as e:
                logger.info("Error with JWT token: %s", e)

                return HttpResponseForbidden()
        else:
            logger.info("No JWT token found.")

            return HttpResponseForbidden()

        user = User.objects.filter(id=request.POST.get("user")).first()

        if not user or not user.is_authenticated:
            raise ChunkedUploadError(
                status=http_status.HTTP_403_FORBIDDEN,
                detail="Authentication credentials were not provided.",
            )

    def on_completion(self, uploaded_file, request):
        user = User.objects.filter(id=request.POST.get("user")).first()

        filename = request.POST.get("filename")
        filename = pv.sanitize_filename(filename)

        # TODO: Get origin device
        device = "web"

        if not os.path.exists(os.path.join(user.scan_directory, "uploads")):
            os.mkdir(os.path.join(user.scan_directory, "uploads"))
        if not os.path.exists(os.path.join(user.scan_directory, "uploads", device)):
            os.mkdir(os.path.join(user.scan_directory, "uploads", device))

        photo = uploaded_file
        image_hash = calculate_hash_b64(user, io.BytesIO(photo.read()))

        if not Photos.objects.filter(image_hash=image_hash).exists():
            if not os.path.exists(
                os.path.join(user.scan_directory, "uploads", device, filename)
            ):
                photo_path = os.path.join(
                    user.scan_directory, "uploads", device, filename
                )
            else:
                existing_photo_hash = calculate_hash(
                    user, os.path.join(user.scan_directory, "uploads", device, filename)
                )

                file_name = os.path.splitext(os.path.basename(filename))[0]
                file_name_extension = os.path.splitext(os.path.basename(filename))[1]

                if existing_photo_hash == image_hash:
                    # File already exist, do not copy it in the upload folder
                    logger.info(
                        "Photo %s duplicated with hash %s ", filename, image_hash
                    )
                    photo_path = ""
                else:
                    photo_path = os.path.join(
                        user.scan_directory,
                        "uploads",
                        device,
                        file_name + "_" + image_hash + file_name_extension,
                    )

            if photo_path:
                with open(photo_path, "wb") as f:
                    photo.seek(0)
                    f.write(photo.read())

            chunked_upload = get_object_or_404(
                ChunkedUpload, upload_id=request.POST.get("upload_id")
            )
            chunked_upload.delete(delete_file=True)
            photo = create_new_image(user, photo_path)
            AsyncTask(handle_new_image, user, photo_path, image_hash, photo).run()
        else:
            logger.info("Photo %s duplicated with hash %s", filename, image_hash)
