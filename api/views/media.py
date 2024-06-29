"""Media views."""

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from api.models.photos import Photos
from api.utils import logger


class MediaAccessView(APIView):
    permission_classes = (AllowAny,)

    def _get_protected_media_url(self, path, fname):
        return "/protected_media{}/{}".format(path, fname)

    def get(self, request, path, fname, format=None):
        jwt = request.COOKIES.get("jwt")
        image_hash = fname.split(".")[0].split("_")[0]

        try:
            photo = Photos.objects.get(image_hash=image_hash)
        except Photos.DoesNotExist:
            return HttpResponse(status=404)

        # Forbid access if trouble with jwt.
        if jwt is not None:
            try:
                token = AccessToken(jwt)
            except TokenError as e:
                logger.exception("Could not get token: %s", str(e))
                return HttpResponseForbidden()
        else:
            logger.warning("Could not get token.")
            return HttpResponseForbidden()

        match(path.lower()):
            case "thumbnails":
                response = HttpResponse()
                response["Content-Type"] = "image/webp"
                response["X-Accel-Redirect"] = self._get_protected_media_url(
                    "thumbnails", fname + ".webp"
                )

                return response

            case "faces":
                response = HttpResponse()
                response["Content-Type"] = "image/jpg"
                response["X-Accel-Redirect"] = self._get_protected_media_url(path, fname)

                return response

            case "avatars":
                try:
                    response = HttpResponse()
                    response["Content-Type"] = "image/png"
                    response["X-Accel-Redirect"] = "/protected_media/" + path + "/" + fname

                    return response
                except Exception as e:
                    logger.exception("Could not get avatar: %s", str(e))

                    return HttpResponse(status=404)

            case "zip":
                try:
                    filename = fname + str(token["user_id"]) + ".zip"
                    response = HttpResponse()
                    response["Content-Type"] = "application/x-zip-compressed"
                    response["X-Accel-Redirect"] = self._get_protected_media_url(
                        path, filename
                    )

                    return response
                except Exception as e:
                    logger.exception("Could not generate zip: %s", str(e))

                    return HttpResponseForbidden()
            case _:
                return HttpResponse(status=404)