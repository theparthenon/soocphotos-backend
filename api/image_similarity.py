"""Compares images and returns similar ones."""

from datetime import datetime
import logging.handlers

from django.core.paginator import Paginator
from django.db.models import Q

from api.retrieval_index import RetrievalIndex

from api.models import Photos

logger = logging.getLogger("image_similarity")

index = RetrievalIndex()


def search_similar_images(user, photo, threshold=27):
    """Search for similar images."""

    if isinstance(user, int):
        user_id = user
    else:
        user_id = user.id

    try:
        res = index.search_similar(user_id=user_id, thres=threshold, in_embedding=[])

        return res
    except Exception:  # pylint: disable=broad-except
        logger.exception(
            "Error retrieving similar photos to %s belonging to user %s.",
            photo.image_hash,
            user.username,
        )

        return []


def build_image_similarity_index(user):
    """
    Builds the image similarity index for a given user.
    Args:
        user (User): The user for whom the similarity index is being built.
    Returns:
        None
    This function deletes any existing similarity index for the user from the server.
    It then retrieves all photos belonging to the user that are not hidden,
    orders them by image hash, and paginates them into groups of 5000.
    For each page of photos, it extracts the image hashes and sends a POST request
    to the server to build the similarity index for that page.
    The function logs the start and end time of the index building process.
    Note:
        The function assumes that the `settings.IMAGE_SIMILARITY_SERVER` variable
        is set and points to the correct server address.
    """

    logger.info("Building similarity index for user %s", user.username)

    if user.id in index.indices:
        del index.indices[user.id]
        del index.image_hashes[user.id]

    start = datetime.now()
    photos = (
        Photos.objects.filter(Q(hidden=False) & Q(owner=user))
        .only("image_hash")
        .order_by("image_hash")
        .all()
    )
    paginator = Paginator(photos, 5000)

    for page in range(1, paginator.num_pages + 1):
        image_hashes = []

        for photo in paginator.page(page).object_list:
            image_hashes.append(photo.image_hash)

        index.build_index_for_user(
            user_id=user.id, image_hashes=image_hashes, image_embeddings=[]
        )

    elapsed_time = (datetime.now() - start).total_seconds()

    logger.info("building similarity index took %.2f seconds", elapsed_time)
