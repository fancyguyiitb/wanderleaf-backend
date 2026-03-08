from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.bookings.models import Booking
from apps.common.models import TimeStampedModel
from apps.listings.models import Listing
from apps.users.models import User


class Review(TimeStampedModel):
    """
    Review by a guest for a listing, tied to a completed stay (booking).
    One review per booking; only guests who stayed can write reviews.
    """

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="review",
        unique=True,
        null=True,
        blank=True,
        help_text="The completed stay this review is for. Required for new reviews.",
    )
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Star rating from 1 to 5.",
    )
    comment = models.TextField(default="", blank=True, help_text="Written review text.")

