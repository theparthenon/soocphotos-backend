"""Django manager to build image similarity index for all users."""

from django.core.management.base import BaseCommand
from django_q.tasks import AsyncTask

from api.image_similarity import build_image_similarity_index
from api.models import User


class Command(BaseCommand):
    """Django manager command."""

    help = "Build image similarity index for all users"

    def handle(self, *args, **kwargs):
        for user in User.objects.all():
            AsyncTask(build_image_similarity_index, user).run()
