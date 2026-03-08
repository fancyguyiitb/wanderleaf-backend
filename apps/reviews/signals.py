"""
Signals to keep Listing.average_rating and Listing.review_count in sync
when reviews are created or deleted.
"""

from decimal import Decimal

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.listings.models import Listing
from apps.reviews.models import Review


def _update_listing_rating(listing: Listing, delta_count: int, delta_sum: float) -> None:
    """
    Update listing's average_rating and review_count.
    delta_count: +1 for new review, -1 for deleted
    delta_sum: +rating for new, -rating for deleted
    """
    old_count = listing.review_count
    old_avg = float(listing.average_rating)
    old_sum = old_avg * old_count

    new_count = old_count + delta_count
    new_sum = old_sum + delta_sum

    if new_count <= 0:
        listing.average_rating = Decimal("0")
        listing.review_count = 0
    else:
        new_avg = round(new_sum / new_count, 1)
        listing.average_rating = Decimal(str(new_avg))
        listing.review_count = new_count

    listing.save(update_fields=["average_rating", "review_count", "updated_at"])


@receiver(post_save, sender=Review)
def on_review_created(sender, instance, created, **kwargs):
    """When a new review is created, update the listing's cached rating."""
    if not created:
        return
    listing = instance.listing
    _update_listing_rating(listing, delta_count=1, delta_sum=float(instance.rating))


@receiver(pre_delete, sender=Review)
def on_review_deleted(sender, instance, **kwargs):
    """When a review is deleted, update the listing's cached rating."""
    listing = instance.listing
    _update_listing_rating(listing, delta_count=-1, delta_sum=-float(instance.rating))
