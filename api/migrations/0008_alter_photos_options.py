# Generated by Django 5.0.6 on 2024-06-18 16:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_photos_dominant_color_user_save_metadata_to_disk_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="photos",
            options={"ordering": ["-added_on"], "verbose_name_plural": "Photos"},
        ),
    ]
