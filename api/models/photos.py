"""Create Photos model for database."""

import os
from io import BytesIO

import magic
import numpy as np
import PIL
from django.core.files.base import ContentFile
from django.db import models
from django.db.utils import IntegrityError
from taggit.managers import TaggableManager

import api.models
import api.face_extractor as face_extractor
from api.face_recognition import get_face_encodings
from api.image_captioning import generate_caption
from api.image_conversion import (
    does_optimized_image_exist,
    does_thumbnail_exist,
    generate_optimized_image,
    generate_thumbnail,
    generate_thumbnail_for_video,
)
from api.llm import generate_prompt
from api.utils import logger

from .user import User, get_deleted_user


class Photos(models.Model):
    """Photos model initialization."""

    image_hash = models.CharField(primary_key=True, max_length=64, null=False)
    image_size = models.BigIntegerField(default=0)
    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )

    original_image = models.ImageField(upload_to="originals")
    optimized_image = models.ImageField(upload_to="optimized")
    thumbnail = models.ImageField(upload_to="thumbnails")
    added_on = models.DateTimeField(auto_now_add=True)

    captions_json = models.JSONField(blank=True, null=True, db_index=True)
    geolocation_json = models.JSONField(blank=True, null=True, db_index=True)
    exif_json = models.JSONField(blank=True, null=True)

    exif_gps_lat = models.FloatField(blank=True, null=True)
    exif_gps_lon = models.FloatField(blank=True, null=True)
    exif_timestamp = models.DateTimeField(blank=True, null=True)

    search_captions = models.TextField(blank=True, null=True, db_index=True)
    search_location = models.TextField(blank=True, null=True, db_index=True)

    rating = models.IntegerField(default=0, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)
    hidden = models.BooleanField(default=False, db_index=True)
    video = models.BooleanField(default=False)
    video_length = models.TextField(blank=True, null=True)

    tags = TaggableManager()

    objects = models.Manager()

    _loaded_values = {}

    def __str__(self):
        return f"{self.image_hash} - {self.owner} - {self.added_on} - {self.rating}"

    @classmethod
    def from_db(cls, db, field_names, values):
        """Save original values when model is loaded from database in a separate
        attribute on the model."""

        instance = super().from_db(db, field_names, values)
        instance._loaded_values = dict(zip(field_names, values))

        return instance

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        """Save the current instance of the model to the database."""

        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def _extract_faces(self, second_try=False):
        unknown_cluster: api.models.cluster.Cluster = (
            api.models.cluster.get_unknown_cluster(user=self.owner)
        )

        try:
            optimized_image = np.array(PIL.Image.open(self.optimized_image.path))
            face_locations = face_extractor.extract(
                self.original_image.path, self.optimized_image.path, self.owner
            )

            if len(face_locations) == 0:
                return

            face_encodings = get_face_encodings(
                self.optimized_image.path, known_face_locations=face_locations
            )

            for idx_face, face in enumerate(zip(face_encodings, face_locations)):
                face_encoding = face[0]
                face_location = face[1]

                top, right, bottom, left, person_name = face_location

                if person_name:
                    person = api.models.person.get_or_create_person(
                        name=person_name, owner=self.owner
                    )
                    person.save()
                else:
                    person = api.models.person.get_unknown_person(owner=self.owner)

                face_image = optimized_image[top:bottom, left:right]
                face_image = PIL.Image.fromarray(face_image)

                image_path = self.image_hash + "_" + str(idx_face) + ".jpg"

                margin = int((right - left) * 0.05)
                existing_faces = api.models.face.Face.objects.filter(
                    photo=self,
                    location_top__lte=top + margin,
                    location_top__gte=top - margin,
                    location_right__lte=right + margin,
                    location_right__gte=right - margin,
                    location_bottom__lte=bottom + margin,
                    location_bottom__gte=bottom - margin,
                    location_left__lte=left + margin,
                    location_left__gte=left - margin,
                )

                if existing_faces.count() != 0:
                    continue

                face = api.models.face.Face(
                    photo=self,
                    location_top=top,
                    location_right=right,
                    location_bottom=bottom,
                    location_left=left,
                    encoding=face_encoding.tobytes().hex(),
                    person=person,
                    cluster=unknown_cluster,
                )

                if person_name:
                    person._calculate_face_count()
                    person._set_default_cover_photo()

                face_io = BytesIO()
                face_image.save(face_io, format="JPEG")
                face_image.save(image_path, ContentFile(face_io.getvalue()))
                face_io.close()
                face.save()
            logger.info("image %s: scanned %s faces", self, len(face_locations))
        except IntegrityError:
            # When using multiple processes, then we can save at the same time,
            # which leads to this error
            if self.original_image.path.exists():
                # Print out the location of the image only if we have a path
                logger.info("image %s: rescan face failed", self.original_image.path)

            if not second_try:
                self._extract_faces(True)
            else:
                if self.original_image.path.exists():
                    logger.error(
                        "image %s: rescan face failed", self.original_image.path
                    )
                else:
                    logger.error("image %s: rescan face failed", self)
        except Exception as e:
            logger.error("image %s: scan face failed", self)

            raise e

    def _geolocate(self, commit=True):
        pass

    def _generate_captions(self, commit=True):
        try:
            image_path = self.optimized_image.path
            confidence = self.owner.confidence
            json = {
                "image_path": image_path,
                "confidence": confidence,
            }

            # TODO: plug in res_places365
            res_places365 = None

            if self.captions_json is None:
                self.captions_json = {}

            self.captions_json["places365"] = res_places365
            self._recreate_search_captions()

            if commit:
                self.save()

            logger.info("Generated places365 captions for image %s.", image_path)
        except Exception as e:
            logger.exception("Could not generate captions for image %s", image_path)

            raise e

    def _recreate_search_captions(self):
        search_captions = ""

        if self.captions_json:
            places365_captions = self.captions_json.get("places365", {})

            attributes = places365_captions.get("attributes", [])
            search_captions += " ".join(attributes) + " "

            categories = places365_captions.get("categories", [])
            search_captions += " ".join(categories) + " "

            environment = places365_captions.get("environment", "")
            search_captions += environment + " "

            user_caption = self.captions_json.get("user_caption", "")
            search_captions += user_caption + " "

        for face in api.models.face.Face.objects.filter(photo=self).all():
            search_captions += face.person.name + " "

        if self.video:
            search_captions += "type: video "

        self.search_captions = search_captions.strip()  # Remove trailing space
        logger.debug(
            "Recreated search captions for image %s.", self.optimized_image.path
        )
        self.save()

    def _generate_captions_im2txt(self, commit=True):
        image_path = self.optimized_image.path
        captions = self.captions_json
        current_user = User.objects.get(username=self.owner)

        try:
            if current_user.captions_model == "NONE":
                logger.info("Generating captions is disabled.")

                return False

            onnx = False

            if current_user.captions_model == "IM2TXT_ONNX":
                onnx = True

            blip = False

            if current_user.captions_model == "BLIP":
                blip = True

            caption = generate_caption(image_path=image_path, blip=blip, onnx=onnx)
            caption = caption.replace("<start>", "").replace("<end>", "").strip()

            llm_settings = current_user.llm_settings

            if llm_settings["enabled"]:
                face = api.models.face.Face.objects.filter(photo=self).first()
                person_name = ""

                if face and llm_settings["add_person"]:
                    person_name = " Person: " + face.person.name

                place = ""

                if self.search_location and llm_settings["add_location"]:
                    place = " Place: " + self.search_location

                keywords = ""

                if llm_settings["add_keywords"]:
                    keywords = " and tags or keywords"

                prompt = (
                    "Q: Your task is to improve the following image caption: "
                    + caption
                    + ". You also know the following information about the image:"
                    + place
                    + person_name
                    + ". Stick as closely as possible to the caption, while replacing generic information with information you know about the image. Only output the caption"  # pylint: disable=line-too-long
                    + keywords
                    + ". \n A:"
                )
                # logger.info(prompt) TODO: Log function
                caption = generate_prompt(prompt)

            captions["im2txt"] = caption
            self.captions_json = captions
            self._recreate_search_captions()

            if commit:
                self.save()

            logger.info(
                "Generated im2txt captions for image %s with SiteConfig %s with Blip: %s and Onnx: %s caption: %s",  # pylint: disable=line-too-long
                image_path,
                current_user.captions_model,
                blip,
                onnx,
                caption,
            )

            return True
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Could not generate im2txt captions for image %s", image_path
            )

            return False

    def _generate_optimized_image(self):
        try:
            if not does_optimized_image_exist("optimized", self.image_hash):
                generate_optimized_image(
                    input_path=self.original_image.path,
                    output_path="optimized",
                    image_hash=self.image_hash,
                    file_type=".webp",
                    quality=85,
                )
        except Exception:  # pylint: disable=broad-except
            logger.exception("Could not generate optimized image for image %s", self)

    def _generate_thumbnail(self, commit=True):
        try:
            if not does_thumbnail_exist("thumbnails", self.image_hash):
                if not self.video:
                    generate_thumbnail(
                        input_path=self.original_image.path,
                        output_path="thumbnails",
                        image_hash=self.image_hash,
                        file_type=".webp",
                    )
                else:
                    generate_thumbnail_for_video(
                        input_path=self.original_image.path,
                        output_path="thumbnails",
                        image_hash=self.image_hash,
                        file_type=".webp",
                    )

            filetype = ".webp"

            if self.video:
                filetype = ".mp4"

            self.optimized_image.name = os.path.join(
                "optimized", self.image_hash + ".webp"
            ).strip()
            self.thumbnail.name = os.path.join("thumbnails", self.image_hash + filetype)

            if commit:
                self.save()

        except Exception:  # pylint: disable=broad-except
            logger.exception("Could not generate thumbnail for image %s", self)

    def _has_exif_data(self):
        pass

    def manual_delete(self):
        """
        Deletes the original image, optimized image, and thumbnail associated
        with this object from the file system.

        :return: The result of calling the `delete()` method on this object.
        :raises Exception: If there is an error while deleting the files.
        """

        try:
            if os.path.isfile(self.original_image.path):
                logger.info("Removing photo %s", self.original_image.path)
                os.remove(self.original_image.path)
                os.remove(self.optimized_image.path)
                os.remove(self.thumbnail.path)

            return self.delete()
        except Exception as e:
            logger.exception("Could not delete photo %s", self)
            raise e

    def _save_captions(self, commit=True, caption=None):
        image_path = self.optimized_image.path

        try:
            caption = caption.replace("<start>", "").replace("<end>", "").strip()
            self.captions_json["user_caption"] = caption
            self._recreate_search_captions()

            if commit:
                self.save(update_fields=["captions_json", "search_captions"])

            logger.info(
                "saved captions for image %s. caption: %s. captions_json: %s.",
                image_path,
                caption,
                self.captions_json,
            )

            hashtags = [
                word
                for word in caption.split()
                if word.startswith("#") and len(word) > 1
            ]

            for hashtag in hashtags:
                self.tags.add(hashtag)

            return True
        except Exception:  # pylint: disable=broad-except
            logger.exception("could not save captions for image %s", image_path)

            return False

    def _save_metadata(self, modified_fields=None):
        pass


def is_video(path):
    """Check if the provided file path corresponds to a video file."""

    try:
        mime = magic.Magic(mime=True)
        filename = mime.from_file(path)

        return filename.find("video") != -1
    except Exception as e:
        logger.error("could not determine if %s is a video", path)

        raise e
