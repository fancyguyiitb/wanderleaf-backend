from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(TimeStampedModel, AbstractUser):
    """
    Custom user model.

    We will later switch to email-based authentication and add profile fields
    (e.g. avatar, is_host) as needed.
    """

    # Placeholder for future custom fields
    pass

