"""
Celery tasks for bookings.
"""
from celery import shared_task

from apps.bookings.services import BookingService


@shared_task
def cancel_expired_pending_booking(booking_id: str) -> None:
    """
    Cancel a single PENDING_PAYMENT booking if it has exceeded the 15-minute window.
    Scheduled when the booking is created; revoked when payment succeeds.
    """
    from apps.bookings.models import Booking

    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return
    BookingService.check_and_cancel_expired(booking)
