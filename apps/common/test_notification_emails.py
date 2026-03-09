from datetime import date, timedelta
from decimal import Decimal

from apps.bookings.models import Booking
from apps.common.email_service import NotificationEmailService
from apps.listings.models import Listing
from apps.users.models import User


def send_sample_notification_emails(
    *,
    target_email: str,
    guest_name: str = "Test Guest",
    host_name: str = "Test Host",
    listing_title: str = "Demo Forest Cabin",
) -> None:
    guest = _build_user(
        email=target_email,
        username=guest_name,
    )
    host = _build_user(
        email=target_email,
        username=host_name,
    )
    listing = _build_listing(
        host=host,
        title=listing_title,
    )

    created_booking = _build_booking(
        listing=listing,
        guest=guest,
        status=Booking.Status.PENDING_PAYMENT,
    )
    cancelled_booking = _build_booking(
        listing=listing,
        guest=guest,
        status=Booking.Status.CANCELLED_BY_GUEST,
    )
    confirmed_booking = _build_booking(
        listing=listing,
        guest=guest,
        status=Booking.Status.CONFIRMED,
    )

    NotificationEmailService.send_booking_created(created_booking)
    NotificationEmailService.send_booking_cancelled(
        booking=cancelled_booking,
        cancelled_by=guest,
        refund_code="refund_initiated",
    )
    NotificationEmailService.send_payment_success(confirmed_booking)
    NotificationEmailService.send_payment_failed(
        created_booking,
        reason="verification_failed",
    )
    NotificationEmailService.send_payment_failed(
        created_booking,
        reason="expired",
    )


def _build_user(*, email: str, username: str) -> User:
    return User(
        email=email,
        username=username,
    )


def _build_listing(*, host: User, title: str) -> Listing:
    return Listing(
        host=host,
        title=title,
        description="Sample listing used for notification testing.",
        location="Test Location",
        category="cabins",
        price_per_night=Decimal("4500.00"),
        bedrooms=2,
        bathrooms=Decimal("1.0"),
        max_guests=4,
        amenities=["WiFi", "Kitchen"],
        images=["https://example.com/listing.jpg"],
        is_active=True,
    )


def _build_booking(*, listing: Listing, guest: User, status: str) -> Booking:
    return Booking(
        listing=listing,
        guest=guest,
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=10),
        num_guests=2,
        price_per_night=Decimal("4500.00"),
        num_nights=3,
        subtotal=Decimal("13500.00"),
        service_fee=Decimal("1620.00"),
        cleaning_fee=Decimal("250.00"),
        total_price=Decimal("15370.00"),
        status=status,
        cancellation_reason="Guest changed plans.",
    )
