from django.db import models

from apps.common.models import TimeStampedModel
from apps.listings.models import Listing
from apps.users.models import User


class Booking(TimeStampedModel):
    """
    Skeleton booking model.

    Real fields (check-in/out dates, price, status, etc.) will be added later.
    """

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings")
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")

