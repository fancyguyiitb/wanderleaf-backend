"""
Seed script: create reviews for properties based on existing bookings.

Creates one review per booking for confirmed/completed stays.
Uses the Django ORM directly (no API, no auth required).

Usage:
    1. Ensure Django can connect to the database (migrations applied).
    2. Run:  python seed_reviews.py

    To also mark pending_payment bookings as confirmed (for seeding reviews
    when you have no confirmed bookings yet):
        python seed_reviews.py --confirm-pending

    To delete all existing reviews and re-create from scratch:
        python seed_reviews.py --reset

Prerequisites:
    - Users and listings seeded (seed_users.py, seed_listings.py)
    - Bookings seeded (seed_bookings.py or seed_all.py)
    - For reviews to be created, bookings must be CONFIRMED or COMPLETED.
      Use --confirm-pending to convert pending bookings to confirmed.
"""

import os
import sys
import random
import argparse

# Add project root and set up Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.core.exceptions import ObjectDoesNotExist

from apps.bookings.models import Booking
from apps.reviews.models import Review

# Sample comments by rating (1-5 stars)
COMMENTS_BY_RATING = {
    5: [
        "Absolutely stunning property! The views are breathtaking and the host was incredibly helpful. Highly recommend!",
        "Perfect location and top-notch amenities. Everything was clean and well-maintained. Will definitely stay again!",
        "Exceeded all expectations. Beautiful place, responsive host, and a memorable experience. Five stars!",
        "Best stay we've ever had. The property is even more beautiful in person. Can't wait to come back.",
        "Outstanding! Every detail was thought of. Felt like a true home away from home. Thank you!",
        "Incredible experience from start to finish. The host went above and beyond. Highly recommended!",
    ],
    4: [
        "Great experience overall. Beautiful property and peaceful location. Minor WiFi hiccup but nothing major.",
        "Very nice stay. Clean, comfortable, and as described. Would stay again!",
        "Lovely property with excellent amenities. Host was responsive. Only small issue was check-in timing.",
        "Solid choice. Good value for money. The area is fantastic for exploring. Would recommend.",
        "Nice place, clean and well-kept. Kitchen was well-equipped. Enjoyed our stay!",
    ],
    3: [
        "Decent stay. Property is okay but could use some updates. Location is good.",
        "It was fine. Clean but basic. Good for a short trip. Host was friendly.",
        "Average experience. Some amenities didn't work as expected. Location was convenient though.",
    ],
    2: [
        "Had some issues during our stay. Property needs maintenance. Host was apologetic.",
        "Disappointing. Not as described. Communication could have been better.",
    ],
    1: [
        "Would not recommend. Several problems that weren't addressed.",
    ],
}


def pick_rating_and_comment() -> tuple[int, str]:
    """Pick a rating (1-5) and matching comment. Bias toward 4-5 stars."""
    weights = [0.02, 0.03, 0.10, 0.30, 0.55]  # 1, 2, 3, 4, 5 stars
    rating = random.choices([1, 2, 3, 4, 5], weights=weights)[0]
    comment = random.choice(COMMENTS_BY_RATING[rating])
    return rating, comment


def seed(confirm_pending: bool = False, reset: bool = False) -> tuple[int, int]:
    if reset:
        deleted, _ = Review.objects.all().delete()
        print(f"  Deleted {deleted} existing review(s).\n")

    if confirm_pending:
        pending = Booking.objects.filter(status=Booking.Status.PENDING_PAYMENT)
        count = pending.count()
        if count > 0:
            updated = pending.update(status=Booking.Status.CONFIRMED)
            print(f"  Marked {updated} pending bookings as CONFIRMED.\n")
        else:
            print("  No pending bookings to confirm.\n")

    bookings = (
        Booking.objects
        .filter(status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED])
        .select_related("listing", "guest")
        .order_by("listing", "created_at")
    )

    created = 0
    skipped = 0

    for booking in bookings:
        try:
            booking.review
            skipped += 1
            continue
        except ObjectDoesNotExist:
            pass

        rating, comment = pick_rating_and_comment()
        Review.objects.create(
            booking=booking,
            listing=booking.listing,
            author=booking.guest,
            rating=rating,
            comment=comment,
        )
        created += 1
        print(
            f"  [{created}] {booking.listing.title[:40]}... | "
            f"Guest: {booking.guest.username} | {rating} stars"
        )

    return created, skipped


def main():
    parser = argparse.ArgumentParser(description="Seed reviews for properties based on bookings.")
    parser.add_argument(
        "--confirm-pending",
        action="store_true",
        help="Mark pending_payment bookings as confirmed so they can receive reviews.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing reviews before seeding (re-creates from scratch).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SEED REVIEWS — Based on existing bookings")
    print("=" * 60)

    steps = []
    if args.reset:
        steps.append("Resetting (delete existing reviews)")
    if args.confirm_pending:
        steps.append("Confirming pending bookings")
    steps.append("Creating reviews")

    for i, step in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {step}...")

    created, skipped = seed(confirm_pending=args.confirm_pending, reset=args.reset)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Reviews created:  {created}")
    print(f"  Skipped (already had review): {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    main()
