"""Functions used to covert image format, quality, and size."""

import os
import subprocess
from PIL import Image
from pillow_heif import register_heif_opener

from django.conf import settings


def generate_optimized_image(
    input_path, output_path, image_hash, file_type, quality=85
):
    """Generate an optimized image from the given image."""

    register_heif_opener()

    final_path = os.path.join(
        settings.MEDIA_ROOT, output_path, image_hash + file_type
    ).strip()
    img = Image.open(input_path)
    img.save(final_path, "webp", quality=quality)

    return img


def generate_thumbnail(input_path, output_path, image_hash, file_type):
    """Generate a thumbnail image from the given image."""

    register_heif_opener()

    final_path = os.path.join(
        settings.MEDIA_ROOT, output_path, image_hash + file_type
    ).strip()
    img = Image.open(input_path)
    img.thumbnail((200, 200))
    img.save(final_path, "webp")

    return img


def does_optimized_image_exist(output_path, image_hash):
    """Check if an optimized image exists in the specified output path and with
    the given image_hash."""

    return os.path.exists(
        os.path.join(
            settings.MEDIA_ROOT,
            output_path,
            image_hash + ".webp",
        ).strip()
    )


def does_thumbnail_exist(output_path, image_hash):
    """Check if a thumbnail image exists in the specified output path and with
    the given image_hash."""

    return os.path.exists(
        os.path.join(
            settings.MEDIA_ROOT,
            output_path,
            image_hash + ".webp",
        ).strip()
    )


def does_video_thumbnail_exist(output_path, image_hash):
    """Check if a video thumbnail image exists in the specified output path and
    with the given image_hash."""

    return os.path.exists(
        os.path.join(
            settings.MEDIA_ROOT,
            output_path,
            image_hash + ".mp4",
        ).strip()
    )


def generate_thumbnail_for_video(input_path, output_path, image_hash, file_type):
    """Generate a video thumbnail from the given video."""

    try:
        output = os.path.join(
            settings.MEDIA_ROOT, output_path, image_hash + file_type
        ).strip()
        command = [
            "ffmpeg",
            "-i",
            input_path,
            "-ss",
            "00:00:00.000",
            "-vframes",
            "1",
            output,
        ]

        with subprocess.Popen(command) as proc:
            proc.wait()
    except Exception as e:
        # Could not create thumbnail for video file
        # logger.error(
        #     "Could not create thumbnail for video file {}".format(input_path)
        # )
        raise e
