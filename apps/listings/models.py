from django.db import models

from apps.common.models import TimeStampedModel


class Listing(TimeStampedModel):
    """
    Skeleton model for a property/listing.

    Real fields (title, description, price, location, etc.) will be added later.
    """

    name = models.CharField(max_length=255)


