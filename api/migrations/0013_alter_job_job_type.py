# Generated by Django 5.0.6 on 2024-06-29 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_albumauto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='job_type',
            field=models.PositiveIntegerField(choices=[(1, 'Scan Photos'), (2, 'Scan Faces'), (3, 'Train Faces'), (4, 'Find Similar Faces'), (5, 'Delete Missing Photos'), (6, 'Download Selected Photos'), (7, 'Download Models'), (8, 'Generate Event Albums'), (9, 'Regenerate Event Titles')]),
        ),
    ]