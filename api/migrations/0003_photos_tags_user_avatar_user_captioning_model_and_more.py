# Generated by Django 5.0.6 on 2024-06-13 14:51

import api.models.user
import django.core.validators
import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_photos"),
        (
            "taggit",
            "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="photos",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="avatars"),
        ),
        migrations.AddField(
            model_name="user",
            name="captioning_model",
            field=models.TextField(
                choices=[
                    ("None", "None"),
                    ("im2txt_onnx", "Im2Txt Onnx"),
                    ("blip_base_capfilt_large", "Blip"),
                ],
                default="im2txt_onnx",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="cluster_selection_epsilon",
            field=models.FloatField(default=0.05),
        ),
        migrations.AddField(
            model_name="user",
            name="confidence",
            field=models.FloatField(db_index=True, default=0.1),
        ),
        migrations.AddField(
            model_name="user",
            name="confidence_person",
            field=models.FloatField(default=0.9),
        ),
        migrations.AddField(
            model_name="user",
            name="confidence_unknown_face",
            field=models.FloatField(default=0.5),
        ),
        migrations.AddField(
            model_name="user",
            name="face_recognition_model",
            field=models.TextField(
                choices=[("HOG", "Hog"), ("CNN", "Cnn")], default="HOG"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="favorite_min_rating",
            field=models.IntegerField(db_index=True, default=4),
        ),
        migrations.AddField(
            model_name="user",
            name="llm_settings",
            field=models.JSONField(default=api.models.user.get_default_llm_settings),
        ),
        migrations.AddField(
            model_name="user",
            name="min_cluster_size",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="min_samples",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="user",
            name="semantic_search_topk",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="transcode_videos",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="Cluster",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cluster_id", models.IntegerField(null=True)),
                ("mean_face_encoding", models.TextField()),
                ("name", models.TextField(null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=models.SET(api.models.user.get_deleted_user),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Face",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("image", models.ImageField(null=True, upload_to="faces")),
                (
                    "person_label_is_inferred",
                    models.BooleanField(db_index=True, default=False),
                ),
                (
                    "person_label_probability",
                    models.FloatField(db_index=True, default=0.0),
                ),
                ("location_top", models.IntegerField()),
                ("location_bottom", models.IntegerField()),
                ("location_left", models.IntegerField()),
                ("location_right", models.IntegerField()),
                ("encoding", models.TextField()),
                (
                    "cluster",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="faces",
                        to="api.cluster",
                    ),
                ),
                (
                    "photo",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="faces",
                        to="api.photos",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        validators=[django.core.validators.MinLengthValidator(1)],
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("USER", "User Labelled"),
                            ("CLUSTER", "Cluster ID"),
                            ("UNKNOWN", "Unknown Person"),
                        ],
                        max_length=10,
                    ),
                ),
                ("face_count", models.IntegerField(default=0)),
                (
                    "cluster_owner",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owner",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cover_face",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="face",
                        to="api.face",
                    ),
                ),
                (
                    "cover_photo",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="person",
                        to="api.photos",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="face",
            name="person",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="faces",
                to="api.person",
            ),
        ),
        migrations.AddField(
            model_name="cluster",
            name="person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="clusters",
                to="api.person",
            ),
        ),
    ]
