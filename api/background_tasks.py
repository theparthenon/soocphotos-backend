# pylint: disable=protected-access
"""Background tasks for the API."""

from api.models import Photos
from api.utils import logger


def generate_captions(overwrite=False):
    """
    Generates captions for photos in the database.

    Args:
        overwrite (bool, optional): If True, generates captions for all photos in the database.
                                   If False (default), generates captions only for photos without
                                   captions.

    Returns:
        None

    This function retrieves all photos from the database or only those without captions, depending
    on the value of the `overwrite` parameter. For each photo, it logs the path of the main file
    and calls the `_generate_captions` method to generate captions. After generating captions, the
    photo object is saved.

    Note:
        - The function uses the `Photos` model to retrieve photos from the database.
        - The function logs the number of photos to be processed for caption generation using the
          `logger` module.
        - The function logs the path of each photo before generating captions.
        - The function calls the `_generate_captions` method on each photo object to generate
          captions.
        - The function saves each photo object after generating captions.

    """

    if overwrite:
        photos = Photos.objects.all()
    else:
        photos = Photos.objects.filter(search_captions=None)
    logger.info("%d photos to be processed for caption generation", photos.count())
    for photo in photos:
        logger.info("generating captions for %s", photo.main_file.path)
        photo._generate_captions()
        photo.save()


def geolocate(overwrite=False):
    """
    Geolocates photos based on the given overwrite flag.
    Args:
        overwrite (bool, optional): If True, all photos will be geolocated. If False, only
        photos with empty geolocation_json field will be geolocated. Defaults to False.
    Returns:
        None
    Raises:
        ValueError: If the photo cannot be geolocated.
    Description:
        This function retrieves photos from the database based on the given overwrite flag.
        If overwrite is True, all photos will be retrieved. Otherwise, only photos with empty
        geolocation_json field will be retrieved. The function then logs the number of photos
        to be geolocated using the logger module. For each photo, it logs the path of the photo
        before geolocating it. The function calls the _geolocate and _add_location_to_album_dates
        methods on each photo object to geolocate and add location to album dates respectively.
        If any error occurs during geolocation, a ValueError is raised and logged using the
        logger module.
    """

    if overwrite:
        photos = Photos.objects.all()
    else:
        photos = Photos.objects.filter(geolocation_json={})
    logger.info("%d photos to be geolocated", photos.count())
    for photo in photos:
        try:
            logger.info("geolocating %s", photo.main_file.path)
            photo._geolocate()
            photo._add_location_to_album_dates()
        except ValueError:
            logger.exception("could not geolocate photo: %s", photo)
