"""Create cache model for database."""

from datetime import datetime

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save

from api.models.face import Face
from api.models.person import Person
from api.models.photos import Photos


def change_api_updated_at(sender=None, instance=None, *args, **kwargs):
    """Updates the 'api_updated_at_timestamp' in the cache with the current UTC datetime."""

    cache.set("api_updated_at_timestamp", datetime.now(datetime.UTC))


for model in [Person, Face, Photos]:
    post_save.connect(receiver=change_api_updated_at, sender=model)
    post_delete.connect(receiver=change_api_updated_at, sender=model)
