from django.db import models

from apps.common.models import TimeStampedModel
from apps.listings.models import Listing
from apps.users.models import User


class Review(TimeStampedModel):
    """
    Skeleton review model for listings.
    """

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(default=5)

