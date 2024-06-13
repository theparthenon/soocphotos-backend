"""Face extraction functions."""

import numpy as np
import PIL

from api.exif_tags import Tags
from api.face_recognition import get_face_locations
from api.utils import get_metadata, is_number, logger


class RuleTypes:
    """Rule type options."""

    EXIF = "exif"
    DLIB = "dlib"


def extract_from_exif(image_path, optimized_image):
    """Extracts face locations from an image using EXIF metadata."""

    (region_info, orientation) = get_metadata(
        image_path,
        tags=[Tags.REGION_INFO, Tags.ORIENTATION],
        struct=True,
    )

    if not region_info:
        return

    logger.debug("Extracted region_info for %s", image_path)
    logger.debug("region_info: %s", region_info)
    face_locations = []

    for region in region_info["RegionList"]:
        if region.get("Type") != "Face":
            continue
        person_name = region.get("Name")

        area = region.get("Area")
        applied_to_dimensions = region.get("AppliedToDimensions")
        optimized_image = np.array(PIL.Image.open(optimized_image))

        if (area and area.get("Unit") == "normalized") or (
            applied_to_dimensions and applied_to_dimensions.get("Unit") == "pixel"
        ):
            image_width = optimized_image.shape[1]
            image_height = optimized_image.shape[0]

            if (
                not is_number(area.get("X"))
                or not is_number(area.get("Y"))
                or not is_number(area.get("W"))
                or not is_number(area.get("H"))
            ):
                logger.info(
                    "Broken face area exif data! No numerical positional data. region_info: %s",
                    region_info,
                )

                continue

            correct_w = float(area.get("W"))
            correct_h = float(area.get("H"))
            correct_x = float(area.get("X"))
            correct_y = float(area.get("Y"))

            if orientation == "Rotate 90 CW":
                temp_x = correct_x
                correct_x = 1 - correct_y
                correct_y = temp_x
                correct_w, correct_h = correct_h, correct_w

            elif orientation == "Mirror horizontal":
                correct_x = 1 - correct_x

            elif orientation == "Rotate 180":
                correct_x = 1 - correct_x
                correct_y = 1 - correct_y

            elif orientation == "Mirror vertical":
                correct_y = 1 - correct_y

            elif orientation == "Mirror horizontal and rotate 270 CW":
                temp_x = correct_x
                correct_x = 1 - correct_y
                correct_y = temp_x
                correct_w, correct_h = correct_h, correct_w

            elif orientation == "Mirror horizontal and rotate 90 CW":
                temp_x = correct_x
                correct_x = correct_y
                correct_y = 1 - temp_x
                correct_w, correct_h = correct_h, correct_w

            elif orientation == "Rotate 270 CW":
                temp_x = correct_x
                correct_x = correct_y
                correct_y = 1 - temp_x
                correct_w, correct_h = correct_h, correct_w

            # Calculate the half-width and half-height of the box
            half_width = (correct_w * image_width) / 2
            half_height = (correct_h * image_height) / 2

            # Calculate the top, right, bottom, and left coordinates
            top = int((correct_y * image_height) - half_height)
            right = int((correct_x * image_width) + half_width)
            bottom = int((correct_y * image_height) + half_height)
            left = int((correct_x * image_width) - half_width)

            face_locations.append((top, right, bottom, left, person_name))

    return face_locations


def extract_from_dlib(image_path, optimized_image, owner):
    """Extracts face locations from a given image using the dlib library."""

    try:
        face_locations = get_face_locations(
            optimized_image,
            model=owner.face_recognition_model.lower(),
        )

    except Exception as e:  # pylint: disable=broad-except
        logger.info("Can't extract face information on photo: %s", image_path)
        logger.info(e)

    for i, face_location in enumerate(face_locations):
        face_locations[i] = (*face_location, None)

    return face_locations


def extract(image_path, optimized_image, owner):
    """Extracts face information from an image using either EXIF metadata or Dlib."""

    exif = extract_from_exif(image_path, optimized_image)

    if not exif:
        return extract_from_dlib(image_path, optimized_image, owner)

    return exif
