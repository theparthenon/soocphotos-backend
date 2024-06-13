"""Miscellaneous utility functions."""

import hashlib
import logging.handlers
import requests

# Most optimal value for performance/memory. Found here:
# https://stackoverflow.com/questions/17731660/hashlib-optimal-size-of-chunks-to-be-used-in-md5-update
BUFFER_SIZE = 65536

logger = logging.getLogger("soocphotos")


def is_number(s):
    """Checks if given string is numeric."""

    try:
        float(s)

        return True
    except ValueError:
        logger.error("could not check if %s is numeric", s)

        return False


def get_metadata(media_file, tags, struct=False):
    """Get the metadata for the given `media_file` and `tags`."""

    json = {
        "tags": tags,
        "media_file": media_file,
        "struct": struct,
    }

    response = requests.post(
        "http://localhost:8010/get-tags", json=json, timeout=120
    ).json()

    return response["values"]


def calculate_hash(user, path):
    """Calculate the MD5 hash of a file at the given `path` and concatenate it
    with the `id` of the `user`."""

    try:
        hash_md5 = hashlib.md5()

        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
                hash_md5.update(chunk)

        return hash_md5.hexdigest() + str(user.id)
    except Exception as e:
        logger.error("could not calculate hash for %s", path)

        raise e


def calculate_hash_b64(user, content):
    """Calculate the MD5 hash of the content using the given `user` information
    and return the hash in base64 format."""

    hash_md5 = hashlib.md5()
    with content as f:
        for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest() + str(user.id)
