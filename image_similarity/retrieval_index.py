"""Builds an index for image retrieval."""

import datetime

import faiss
import numpy as np

from utils import logger  # pylint: disable=import-error

EMBEDDING_SIZE = 512


class RetrievalIndex(object):
    """Retrieval index class."""

    def __init__(self):
        self.indices = {}
        self.image_hashes = {}

    def build_index_for_user(self, user_id, image_hashes, image_embeddings):
        """
        Builds an index for a specific user based on the provided image hashes and image embeddings.
        Parameters:
            user_id (int): The ID of the user for whom the index is built.
            image_hashes (list): List of image hashes for the user.
            image_embeddings (list): List of image embeddings for the user.
        Returns:
            None
        """

        logger.info(
            "building index for user %d - got %d photos to process",
            user_id,
            len(image_hashes),
        )
        start = datetime.datetime.now()
        if not self.indices.get(user_id):
            self.indices[user_id] = faiss.IndexFlatIP(EMBEDDING_SIZE)
        if not self.image_hashes.get(user_id):
            self.image_hashes[user_id] = []

        for h, e in zip(image_hashes, image_embeddings):
            self.image_hashes[user_id].append(h)
            self.indices[user_id].add(np.array([e], dtype=np.float32))

        elapsed = (datetime.datetime.now() - start).total_seconds()
        logger.info(
            "finished building index for user %d - took %.2f seconds", user_id, elapsed
        )

    def search_similar(self, user_id, in_embedding, n=100, thres=27.0):
        """Searches for similar images."""

        start = datetime.datetime.now()
        dist, res_indices = self.indices[user_id].search(
            np.array([in_embedding], dtype=np.float32), n
        )
        res = []
        for distance, idx in sorted(zip(dist[0], res_indices[0]), reverse=True):
            if distance >= thres:
                res.append(self.image_hashes[user_id][idx])
        elapsed = (datetime.datetime.now() - start).total_seconds()
        logger.info(
            "searched for %d images for user %d - took %.2f seconds",
            n,
            user_id,
            elapsed,
        )
        return res
