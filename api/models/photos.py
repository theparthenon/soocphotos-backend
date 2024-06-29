# pylint: disable=E1101, W0212
"""Create Photos model for database."""

import json
import numbers
import os
from io import BytesIO
import numpy as np
import PIL
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.db.utils import IntegrityError
import requests
from taggit.managers import TaggableManager

from api import date_time_extractor
from api.exif_tags import Tags
import api.models
from api.models.file import File
import api.face_extractor as face_extractor
from api.face_recognition import get_face_encodings
from api.geocode.geocode import reverse_geocode
from api.image_captioning import generate_caption
from api.image_conversion import (
    does_optimized_image_exist,
    does_thumbnail_exist,
    generate_optimized_image,
    generate_thumbnail,
    generate_thumbnail_for_video,
)
from api.llm import generate_prompt
from api.utils import get_metadata, logger, write_metadata

from .user import User, get_deleted_user


class VisiblePhotoManager(models.Manager):
    """Only show photos that are not hidden or deleted."""

    def get_queryset(self):
        """Get photos that are not hidden or deleted."""

        return super().get_queryset().filter(Q(hidden=False) & Q(deleted=False))


class Photos(models.Model):
    """Photos model initialization."""

    image_hash = models.CharField(primary_key=True, max_length=64, null=False)
    owner = models.ForeignKey(
        User, on_delete=models.SET(get_deleted_user), default=None
    )
    files = models.ManyToManyField(File)
    original_image = models.ForeignKey(
        File,
        related_name="main_photo",
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
    )
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

    timestamp = models.DateTimeField(blank=True, null=True, db_index=True)

    size = models.BigIntegerField(default=0)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    rating = models.IntegerField(default=0, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)
    hidden = models.BooleanField(default=False, db_index=True)
    video = models.BooleanField(default=False)
    video_length = models.TextField(blank=True, null=True)

    dominant_color = models.TextField(blank=True, null=True)

    tags = TaggableManager()

    objects = models.Manager()
    visible = VisiblePhotoManager()

    _loaded_values = {}

    class Meta:
        """Meta class for Photos model."""

        ordering = ["-added_on"]
        verbose_name_plural = "Photos"

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
        save_metadata=True,
    ):
        """Save the current instance of the model to the database."""

        modified_fields = [
            field_name
            for field_name, value in self._loaded_values.items()
            if value != getattr(self, field_name)
        ]
        user = User.objects.get(username=self.owner)

        if save_metadata and user.save_metadata_to_disk != User.SaveMetadata.OFF:
            self._save_metadata(
                modified_fields,
                user.save_metadata_to_disk == User.SaveMetadata.SIDECAR_FILE,
            )

        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def _add_location_to_album_dates(self):
        if not self.geolocation_json:
            return

        album_date = self._find_album_date()
        city_name = self.geolocation_json["places"][-2]

        if album_date.location and len(album_date.location) > 0:
            prev_value = album_date.location
            new_value = prev_value

            if city_name not in prev_value["places"]:
                new_value["places"].append(city_name)
                new_value["places"] = list(set(new_value["places"]))
                album_date.location = new_value
        else:
            album_date.location = {"places": [city_name]}
        # Safe geolocation_json
        album_date.save()

    def _add_to_album_thing(self):
        if (
            type(self.captions_json) is dict
            and "places365" in self.captions_json.keys()
        ):
            for attribute in self.captions_json["places365"]["attributes"]:
                album_thing = api.models.album_thing.get_album_thing(
                    title=attribute,
                    owner=self.owner,
                )

                if album_thing.photos.filter(image_hash=self.image_hash).count() == 0:
                    album_thing.photos.add(self)
                    album_thing.thing_type = "places365_attribute"
                    album_thing.save()

            for category in self.captions_json["places365"]["categories"]:
                album_thing = api.models.album_thing.get_album_thing(
                    title=category,
                    owner=self.owner,
                )

                if album_thing.photos.filter(image_hash=self.image_hash).count() == 0:
                    album_thing = api.models.album_thing.get_album_thing(
                        title=category, owner=self.owner
                    )
                    album_thing.photos.add(self)
                    album_thing.thing_type = "places365_category"
                    album_thing.save()

    def _find_album_date(self):
        old_album_date = None

        if self.exif_timestamp:
            possible_old_album_date = api.models.album_date.get_album_date(
                date=self.exif_timestamp.date(), owner=self.owner
            )

            if (
                possible_old_album_date is not None
                and possible_old_album_date.photos.filter(
                    image_hash=self.image_hash
                ).exists
            ):
                old_album_date = possible_old_album_date
        else:
            possible_old_album_date = api.models.album_date.get_album_date(
                date=None, owner=self.owner
            )

            if (
                possible_old_album_date is not None
                and possible_old_album_date.photos.filter(
                    image_hash=self.image_hash
                ).exists
            ):
                old_album_date = possible_old_album_date

        return old_album_date

    def _find_album_place(self):
        return api.models.album_place.AlbumPlace.objects.filter(
            Q(photos__in=[self])
        ).all()

    def _extract_date_time_from_exif(self, commit=True):
        """Extract date time from photo EXIF data."""

        def exif_getter(tags):
            return get_metadata(self.original_image.path, tags=tags, try_sidecar=True)

        datetime_config = json.loads(self.owner.datetime_rules)
        extracted_local_time = date_time_extractor.extract_local_date_time(
            self.original_image.path,
            date_time_extractor.as_rules(datetime_config),
            exif_getter,
            self.exif_gps_lat,
            self.exif_gps_lon,
            self.owner.default_timezone,
            self.timestamp,
        )

        old_album_date = self._find_album_date()

        if self.exif_timestamp != extracted_local_time:
            self.exif_timestamp = extracted_local_time

        if old_album_date is not None:
            old_album_date.photos.remove(self)
            old_album_date.save()

        album_date = None

        if self.exif_timestamp:
            album_date = api.models.album_date.get_or_create_album_date(
                date=self.exif_timestamp.date(), owner=self.owner
            )
            album_date.photos.add(self)
        else:
            album_date = api.models.album_date.get_or_create_album_date(
                date=None, owner=self.owner
            )
            album_date.photos.add(self)

        if commit:
            self.save()

    def _extract_exif_data(self, commit=True):
        (size, width, height, video_length, rating) = get_metadata(
            self.original_image.path,
            tags=[
                Tags.FILE_SIZE,
                Tags.IMAGE_WIDTH,
                Tags.IMAGE_HEIGHT,
                Tags.QUICKTIME_DURATION,
                Tags.RATING,
            ],
            try_sidecar=True,
        )

        if size and isinstance(size, numbers.Number):
            self.size = size

        if width and isinstance(width, numbers.Number):
            self.width = width

        if height and isinstance(height, numbers.Number):
            self.height = height

        if video_length and isinstance(video_length, numbers.Number):
            self.video_length = video_length

        if rating and isinstance(rating, numbers.Number):
            self.rating = rating

        if commit:
            self.save()

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
                face.image.save(image_path, ContentFile(face_io.getvalue()))
                face_io.close()
                face.save()
            logger.info(
                "image %s: %d face(s) saved", self.image_hash, len(face_locations)
            )
        except IntegrityError:
            # When using multiple processes, then we can save at the same time, which leads to this error
            if self.files.count() > 0:
                # print out the location of the image only if we have a path
                logger.info("image %s: rescan face failed", self.original_image.path)
            if not second_try:
                self._extract_faces(True)
            else:
                if self.files.count() > 0:
                    logger.error(
                        logger.info(
                            "image %s: rescan face failed", self.original_image.path
                        )
                    )
                else:
                    logger.error("image %s: rescan face failed", self)
        except Exception as e:
            logger.error("image %s: scan face failed", self)
            raise e

    def _geolocate(self, commit=True):
        new_gps_lat, new_gps_lon = get_metadata(
            self.original_image.path,
            tags=[Tags.LATITUDE, Tags.LONGITUDE],
            try_sidecar=True,
        )

        self.exif_gps_lat = float(new_gps_lat)
        self.exif_gps_lon = float(new_gps_lon)

        if commit:
            self.save()

        try:
            res = reverse_geocode(new_gps_lat, new_gps_lon)

            if not res:
                return
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(e)
            logger.warning(
                "Something went wrong with geolocating %s", self.original_image
            )

            return

        self.geolocation_json = res
        self.search_location = res["address"]

        # TODO: possibly add places album

        if commit:
            self.save()

    def _generate_captions(self, commit=True):
        try:
            image_path = self.optimized_image.path
            confidence = self.owner.confidence

            json = {
                "image_path": image_path,
                "confidence": confidence,
            }
            res_places365 = requests.post(
                "http://localhost:8011/generate-tags", json=json
            ).json()["tags"]

            if res_places365 is None:
                return

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
            from constance import config as site_config

            if site_config.CAPTIONING_MODEL == "None":
                logger.info("Generating captions is disabled")
                return False

            onnx = False
            if site_config.CAPTIONING_MODEL == "im2txt_onnx":
                onnx = True

            blip = False
            if site_config.CAPTIONING_MODEL == "blip_base_capfilt_large":
                blip = True

            caption = generate_caption(image_path=image_path, blip=blip, onnx=onnx)
            caption = caption.replace("<start>", "").replace("<end>", "").strip()

            llm_settings = current_user.llm_settings

            if site_config.LLM_MODEL != "None" and llm_settings["enabled"]:
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
                site_config.CAPTIONING_MODEL,
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

    def _generate_optimized_image(self, commit=True):
        try:
            if not does_optimized_image_exist("optimized", self.image_hash):
                generate_optimized_image(
                    input_path=self.original_image.path,
                    output_path="optimized",
                    image_hash=self.image_hash,
                    file_type=".webp",
                    quality=85,
                )
            if commit:
                self.save()

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

    def manual_delete(self):
        """
        Deletes the original image, optimized image, and thumbnail associated
        with this object from the file system.

        :return: The result of calling the `delete()` method on this object.
        :raises Exception: If there is an error while deleting the files.
        """

        for file in self.files.all():
            if os.path.isfile(file.path):
                logger.info("Removing photo %s", file.path)
                os.remove(file.path)
                file.delete()

        # TODO: Handle wrong file permissions
        return self.delete()

    def delete_duplicate(self, duplicate_path):
        """
        Deletes a duplicate photo file and updates the `files` field of the current object.
        Args:
            duplicate_path (str): The path of the duplicate photo file to be deleted.
        Returns:
            bool: True if the duplicate photo file was successfully deleted, False otherwise.
        """

        # TODO: Handle wrong file permissions
        for file in self.files.all():
            if file.path == duplicate_path:
                if not os.path.isfile(duplicate_path):
                    logger.info(
                        "Path does not lead to a valid file: %s", duplicate_path
                    )
                    self.files.remove(file)
                    file.delete()
                    self.save()

                    return False

                logger.info("Removing photo %s", duplicate_path)
                os.remove(duplicate_path)
                self.files.remove(file)
                self.save()
                file.delete()

                return True

        logger.info("Path is not valid: %s", duplicate_path)

        return False

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

    def _save_metadata(self, modified_fields=None, use_sidecar=True):
        tags_to_write = {}

        if modified_fields is None or "rating" in modified_fields:
            tags_to_write[Tags.RATING] = self.rating

        if "timestamp" in modified_fields:
            # TODO: only works for files and not sidecar file
            tags_to_write[Tags.DATE_TIME] = self.timestamp

        if tags_to_write:
            write_metadata(
                self.original_image.path, tags_to_write, use_sidecar=use_sidecar
            )

    def _check_files(self):
        for file in self.files.all():
            if not file.path or not os.path.exists(file.path):
                self.files.remove(file)
                file.missing = True
                file.save()

        self.save()

    def _get_dominant_color(self, palette_size=16):
        # Skip if it's already calculated
        if self.dominant_color:
            return

        try:
            # Resize image to speed up processing
            img = PIL.Image.open(self.optimized_image.path)
            img.thumbnail((100, 100))

            # Reduce colors (uses k-means internally)
            paletted = img.convert("P", palette=1, colors=palette_size)

            # Find the color that occurs most often
            palette = paletted.getpalette()
            color_counts = sorted(paletted.getcolors(), reverse=True)
            palette_index = color_counts[0][1]
            dominant_color = palette[palette_index * 3 : palette_index * 3 + 3]
            self.dominant_color = dominant_color
            self.save()
        except ValueError:
            logger.info("Cannot calculate dominant color %s object", self)
