import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(TimeStampedModel, AbstractUser):
    """
    Custom user model.

    - `username` is used as the user's full name (no special validators).
    - `email` and `phone_number` are unique identifiers.
    - `avatar` optionally stores a profile photo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Use a plain CharField for full name, not the default username validators,
    # and allow duplicate names.
    username = models.CharField(max_length=255, blank=False)

    # We authenticate by email instead of username and require email to be unique.
    email = models.EmailField("email address", unique=True, blank=False)

    # We don't use first_name / last_name.
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="User phone number in international format, digits only.",
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        help_text="Profile photo for the user.",
    )
    chat_public_key = models.TextField(blank=True, default="")
    chat_key_algorithm = models.CharField(max_length=64, blank=True, default="")
    chat_key_version = models.PositiveIntegerField(default=0)
    chat_key_uploaded_at = models.DateTimeField(null=True, blank=True)
    chat_private_key_backup = models.TextField(blank=True, default="")
    chat_private_key_backup_iv = models.CharField(max_length=255, blank=True, default="")
    chat_private_key_backup_salt = models.CharField(max_length=255, blank=True, default="")
    chat_private_key_backup_kdf = models.CharField(max_length=64, blank=True, default="")
    chat_private_key_backup_kdf_iterations = models.PositiveIntegerField(default=0)
    chat_private_key_backup_cipher = models.CharField(max_length=64, blank=True, default="")
    chat_private_key_backup_version = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    @property
    def has_chat_key(self) -> bool:
        return bool(self.chat_public_key and self.chat_private_key_backup)

