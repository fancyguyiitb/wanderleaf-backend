from django.db import models

from apps.common.models import TimeStampedModel


class Payment(TimeStampedModel):
    """
    Skeleton payment model.

    Integration details (Stripe, etc.) will be added later.
    """

    reference = models.CharField(max_length=255, unique=True)

