from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.listings.models import Listing


class WishlistItem(TimeStampedModel):
    """
    A user's wishlisted property.
    One user can wishlist a listing only once (unique on user + listing).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
    )

    class Meta:
        unique_together = [["user", "listing"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} → {self.listing.title}"
