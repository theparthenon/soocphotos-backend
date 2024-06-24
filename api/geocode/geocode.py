"""Geocoding utilities."""

import geopy

from django.conf import settings

from api.utils import logger
from .config import get_provider_config, get_provider_parser


class Geocode:
    """Geocode class for geocoding API providers."""

    def __init__(self, provider):
        self._provider_config = get_provider_config(provider)
        self._parser = get_provider_parser(provider)
        self._geocoder = geopy.get_geocoder_for_service(provider)(
            **self._provider_config
        )

    def reverse(self, lat: float, lon: float) -> dict:
        """Reverse geocodes a location using the provided latitude and longitude."""

        if (
            "geocode_args" in self._provider_config
            and "api_key" in self._provider_config["geocode_args"]
            and self._provider_config["geocode_args"]["api_key"] is None
        ):
            logger.warning(
                "No API key found for map provider. Please set MAP_API_KEY in the admin panel or switch map provider."  # pylint: disable=line-too-long
            )
            return {}
        location = self._geocoder.reverse(f"{lat},{lon}")
        return self._parser(location)


def reverse_geocode(lat: float, lon: float) -> dict:
    """Reverse geocodes a location using the provided latitude and longitude."""

    try:
        return Geocode(settings.MAP_API_PROVIDER).reverse(lat, lon)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Error while reverse geocoding: %s", e)
        return {}
