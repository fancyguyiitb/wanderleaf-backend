from apps.bookings.models import Booking
from apps.messaging.models import Conversation


ACTIVE_BOOKING_CHAT_STATUSES = (
    Booking.Status.PENDING_PAYMENT,
    Booking.Status.CONFIRMED,
)


def is_booking_chat_active(booking: Booking) -> bool:
    """Chat is only available while the booking is pending payment or confirmed."""
    return booking.status in ACTIVE_BOOKING_CHAT_STATUSES


def can_access_booking_chat(user, booking: Booking) -> bool:
    """Only the booking guest and the listing host may access the chat."""
    if not getattr(user, "is_authenticated", False):
        return False
    return str(user.id) in {str(booking.guest_id), str(booking.listing.host_id)}


def get_or_create_conversation_for_booking(booking: Booking) -> Conversation:
    """
    Return the single conversation for a booking, keeping participants in sync.
    """
    conversation, _ = Conversation.objects.get_or_create(booking=booking)
    conversation.participants.set([booking.guest, booking.listing.host])
    return conversation

