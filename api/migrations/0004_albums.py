# Generated by Django 5.0.6 on 2024-06-14 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_photos_tags_user_avatar_user_captioning_model_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Albums",
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
                ("album_name", models.TextField()),
                ("photos", models.ManyToManyField(to="api.photos")),
            ],
        ),
    ]
