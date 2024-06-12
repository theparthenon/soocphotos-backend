"""Create User model for database."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """User Model initialization."""

    photo_count = models.IntegerField(default=0)


def get_admin_user():
    """Retrieves the admin user from the database."""

    return User.objects.get(is_superuser=True)


def get_deleted_user():
    """Retrieves the deleted user, or creates it if it doesn't exist."""

    deleted_user: User = User.objects.get_or_create(username="deleted")[0]
    if deleted_user.is_active is not False:
        deleted_user.is_active = False
        deleted_user.save()

    return deleted_user
