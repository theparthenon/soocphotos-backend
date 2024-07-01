"""Miscellaneous utility functions."""

import os
import hashlib
import logging.handlers
import magic
import pyvips
import requests

from exiftool import ExifTool

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


def convert_to_degrees(values):
    """
    Helper function to convert the GPS coordinates stored in the EXIF to degrees in float format
    :param value:
    :type value: exifread.utils.Ratio
    :rtype: float
    """
    d = float(values[0].num) / float(values[0].den)
    m = float(values[1].num) / float(values[1].den)
    s = float(values[2].num) / float(values[2].den)

    return d + (m / 60.0) + (s / 3600.0)


weekdays = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


def get_sidecar_files_in_priority_order(media_file):
    """
    Returns a list of possible XMP sidecar files for *media_file*, ordered
    by priority.

    """
    image_basename = os.path.splitext(media_file)[0]
    return [
        image_basename + ".xmp",
        image_basename + ".XMP",
        media_file + ".xmp",
        media_file + ".XMP",
    ]


def _get_existing_metadata_files_reversed(media_file, include_sidecar_files):
    """Returns a reverse order list of existing metadata files."""

    if include_sidecar_files:
        files = [
            file
            for file in get_sidecar_files_in_priority_order(media_file)
            if os.path.exists(file)
        ]
        files.append(media_file)
        return list(reversed(files))
    return [media_file]


def get_metadata(media_file, tags, try_sidecar=True, struct=False):
    """
    Get values for each metadata tag in *tags* from *media_file*.
    If *try_sidecar* is `True`, use the value set in any XMP sidecar file
    stored alongside *media_file*.
    If *struct* is `True`, use the exiftool instance which returns structured data

    Returns a list with the value of each tag in *tags* or `None` if the
    tag was not found.

    """

    files_by_reverse_priority = _get_existing_metadata_files_reversed(
        media_file, try_sidecar
    )

    json = {
        "tags": tags,
        "files_by_reverse_priority": files_by_reverse_priority,
        "struct": struct,
    }

    response = requests.post(
        "http://localhost:8010/get-tags", json=json, timeout=120
    ).json()

    return response["values"]


def write_metadata(media_file, tags, use_sidecar=True):
    """Write the metadata for the given `media_file` and `tags`."""

    et = ExifTool()
    terminate_et = False

    if not et.running:
        et.start()
        terminate_et = True

    # TODO: Replace with new File Structure
    if use_sidecar:
        file_path = get_sidecar_files_in_priority_order(media_file)[0]
    else:
        file_path = media_file

    try:
        logger.info("Writing %s to %s", tags, file_path)
        params = [os.fsencode(f"-{tag}={value}") for tag, value in tags.items()]
        params.append(b"-overwrite_original")
        params.append(os.fsencode(file_path))
        et.execute(*params)
    finally:
        if terminate_et:
            et.terminate()


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


def is_metadata(path):
    """Check if the provided file path corresponds to a metadata file."""

    file_extension = os.path.splitext(path)[1]
    raw_formats = [
        ".XMP",
    ]

    return file_extension.upper() in raw_formats


def is_raw(path):
    """Check if the provided file path corresponds to a raw file."""

    file_extension = os.path.splitext(path)[1]
    rawformats = [
        ".RWZ",
        ".CR2",
        ".NRW",
        ".EIP",
        ".RAF",
        ".ERF",
        ".RW2",
        ".NEF",
        ".ARW",
        ".K25",
        ".DNG",
        ".SRF",
        ".DCR",
        ".RAW",
        ".CRW",
        ".BAY",
        ".3FR",
        ".CS1",
        ".MEF",
        ".ORF",
        ".ARI",
        ".SR2",
        ".KDC",
        ".MOS",
        ".MFW",
        ".FFF",
        ".CR3",
        ".SRW",
        ".RWL",
        ".J6I",
        ".KC2",
        ".X3F",
        ".MRW",
        ".IIQ",
        ".PEF",
        ".CXI",
        ".MDC",
    ]
    return file_extension.upper() in rawformats


def is_video(path):
    """Check if the provided file path corresponds to a video file."""

    try:
        mime = magic.Magic(mime=True)
        filename = mime.from_file(path)

        return filename.find("video") != -1
    except Exception as e:
        logger.error("could not determine if %s is a video", path)

        raise e


def is_photo(path):
    """Check if the provided file path corresponds to a photo file."""
    file_extension = os.path.splitext(path)[1]
    imgformats = [
        ".TIFF",
        ".JPG",
        ".JPEG",
        ".PNG",
        ".GIF",
        ".HEIF",
        ".HEIC",
        ".BMP",
        ".WEBP",
    ]

    return file_extension.upper() in imgformats


def is_valid_media(path):
    """Check if the provided file path corresponds to a valid media file."""

    if is_video(path) or is_raw(path) or is_metadata(path):
        return True
    try:
        pyvips.Image.thumbnail(path, 10000, height=200, size=pyvips.enums.Size.DOWN)

        return True
    except OSError as e:
        logger.info("Could not handle %s, because %s", path, str(e))

        return False
