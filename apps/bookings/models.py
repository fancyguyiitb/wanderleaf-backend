from datetime import date, timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.listings.models import Listing
from apps.users.models import User


def default_check_in():
    return date.today()


def default_check_out():
    return date.today() + timedelta(days=1)


class Booking(TimeStampedModel):
    """
    Represents a guest's reservation of a listing for a specific date range.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED_BY_GUEST = "cancelled_by_guest", "Cancelled by Guest"
        CANCELLED_BY_HOST = "cancelled_by_host", "Cancelled by Host"
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="The property being booked.",
    )
    guest = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="The user making the reservation.",
    )

    check_in = models.DateField(default=default_check_in, help_text="Check-in date.")
    check_out = models.DateField(default=default_check_out, help_text="Check-out date.")

    num_guests = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of guests for this booking.",
    )

    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Price per night at the time of booking (snapshot).",
    )
    num_nights = models.PositiveIntegerField(
        default=1,
        help_text="Number of nights for the stay.",
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Subtotal (price_per_night * num_nights).",
    )
    service_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Platform service fee charged to the guest.",
    )
    cleaning_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Cleaning fee (if applicable).",
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total amount to be paid (subtotal + fees).",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
        help_text="Current status of the booking.",
    )

    cancellation_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for cancellation (if applicable).",
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when booking was cancelled.",
    )

    special_requests = models.TextField(
        blank=True,
        default="",
        help_text="Any special requests from the guest.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing", "check_in", "check_out"]),
            models.Index(fields=["guest", "status"]),
        ]

    def __str__(self):
        return f"Booking {self.id} - {self.listing.title} ({self.check_in} to {self.check_out})"

    @property
    def is_active(self) -> bool:
        """Returns True if booking is not cancelled or refunded."""
        return self.status in (
            self.Status.PENDING_PAYMENT,
            self.Status.CONFIRMED,
            self.Status.COMPLETED,
        )

    @property
    def can_be_cancelled(self) -> bool:
        """Returns True if booking can still be cancelled."""
        return self.status in (
            self.Status.PENDING_PAYMENT,
            self.Status.CONFIRMED,
        )
