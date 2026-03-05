"""
Cancel PENDING_PAYMENT bookings that are older than 15 minutes.

Run via cron every minute for robustness:
    * * * * * cd /path/to/project && python manage.py cancel_expired_pending_bookings
"""
from django.core.management.base import BaseCommand

from apps.bookings.models import Booking
from apps.bookings.services import BookingService


class Command(BaseCommand):
    help = "Cancel PENDING_PAYMENT bookings older than 15 minutes (payment window expired)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be cancelled without actually cancelling.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        pending = Booking.objects.filter(status=Booking.Status.PENDING_PAYMENT)
        cancelled = 0
        for booking in pending:
            is_expired = BookingService.get_seconds_until_payment_expiry(booking) == 0
            if is_expired:
                if dry_run:
                    cancelled += 1
                    self.stdout.write(
                        self.style.NOTICE(
                            f"  Would cancel: {booking.id} (created {booking.created_at})"
                        )
                    )
                else:
                    if BookingService.check_and_cancel_expired(booking):
                        cancelled += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Cancelled: {booking.id} (created {booking.created_at})"
                            )
                        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"Dry run: would cancel {cancelled} expired pending booking(s)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Cancelled {cancelled} expired pending booking(s).")
            )
