from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Listing(TimeStampedModel):
    """
    A property listing that a host can create and guests can book.
    """

    CATEGORY_CHOICES = [
        ("mountain_retreats", "Mountain Retreats"),
        ("beach_houses", "Beach Houses"),
        ("cabins", "Cabins"),
        ("eco_lodges", "Eco Lodges"),
        ("luxury_villas", "Luxury Villas"),
        ("treehouses", "Treehouses"),
        ("farms", "Farms"),
        ("urban_lofts", "Urban Lofts"),
    ]

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
        help_text="The user who owns/hosts this listing.",
    )

    title = models.CharField(max_length=255, help_text="Listing headline.")
    description = models.TextField(help_text="Full description of the property.")
    location = models.CharField(max_length=255, help_text="Human-readable location string.")
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        blank=True,
        default="",
        help_text="Property category.",
    )

    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Nightly price in USD.",
    )

    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    max_guests = models.PositiveIntegerField(default=2)

    amenities = models.JSONField(
        default=list,
        blank=True,
        help_text="List of amenity strings, e.g. ['WiFi', 'Pool', 'Kitchen'].",
    )

    images = models.JSONField(
        default=list,
        blank=True,
        help_text="List of image URLs for the property.",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS latitude.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS longitude.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Soft-delete / visibility toggle.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.location})"
