from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.bookings.models import Booking
from apps.listings.models import Listing
from apps.payments.models import Payment
from apps.users.models import User


SERVICE_FEE_PERCENTAGE = Decimal("0.12")  # 12% service fee
CLEANING_FEE_DEFAULT = Decimal("25.00")  # Default cleaning fee


@dataclass
class PriceBreakdown:
    """Represents the price breakdown for a booking."""

    price_per_night: Decimal
    num_nights: int
    subtotal: Decimal
    service_fee: Decimal
    cleaning_fee: Decimal
    total_price: Decimal


class BookingService:
    """Service class for booking-related business logic."""

    @staticmethod
    def check_availability(
        listing_id: str,
        check_in: date,
        check_out: date,
        exclude_booking_id: Optional[str] = None,
    ) -> tuple[bool, list[dict]]:
        """
        Check if a listing is available for the given date range.
        
        Returns:
            Tuple of (is_available, conflicting_bookings)
        """
        active_statuses = [
            Booking.Status.PENDING_PAYMENT,
            Booking.Status.CONFIRMED,
        ]

        overlapping_query = Q(
            listing_id=listing_id,
            status__in=active_statuses,
        ) & (
            Q(check_in__lt=check_out, check_out__gt=check_in)
        )

        queryset = Booking.objects.filter(overlapping_query)
        
        if exclude_booking_id:
            queryset = queryset.exclude(id=exclude_booking_id)

        conflicting_bookings = list(
            queryset.values("id", "check_in", "check_out", "status")
        )

        is_available = len(conflicting_bookings) == 0
        return is_available, conflicting_bookings

    @staticmethod
    def get_booked_dates(listing_id: str) -> list[dict]:
        """
        Get all booked date ranges for a listing.
        Returns list of {check_in, check_out} for active bookings.
        """
        active_statuses = [
            Booking.Status.PENDING_PAYMENT,
            Booking.Status.CONFIRMED,
        ]

        bookings = Booking.objects.filter(
            listing_id=listing_id,
            status__in=active_statuses,
            check_out__gte=date.today(),
        ).values("check_in", "check_out")

        return list(bookings)

    @staticmethod
    def calculate_price(
        listing: Listing,
        check_in: date,
        check_out: date,
    ) -> PriceBreakdown:
        """
        Calculate the price breakdown for a booking.
        """
        num_nights = (check_out - check_in).days
        price_per_night = listing.price_per_night
        subtotal = price_per_night * num_nights
        service_fee = (subtotal * SERVICE_FEE_PERCENTAGE).quantize(Decimal("0.01"))
        cleaning_fee = CLEANING_FEE_DEFAULT
        total_price = subtotal + service_fee + cleaning_fee

        return PriceBreakdown(
            price_per_night=price_per_night,
            num_nights=num_nights,
            subtotal=subtotal,
            service_fee=service_fee,
            cleaning_fee=cleaning_fee,
            total_price=total_price,
        )

    @staticmethod
    @transaction.atomic
    def create_booking(
        listing: Listing,
        guest: User,
        check_in: date,
        check_out: date,
        num_guests: int,
        special_requests: str = "",
    ) -> tuple[Booking, Optional[str]]:
        """
        Create a new booking with all validations.
        
        Returns:
            Tuple of (booking, error_message)
        """
        is_available, conflicts = BookingService.check_availability(
            listing_id=str(listing.id),
            check_in=check_in,
            check_out=check_out,
        )

        if not is_available:
            return None, "The listing is not available for the selected dates."

        if num_guests > listing.max_guests:
            return None, f"This listing allows a maximum of {listing.max_guests} guests."

        if str(listing.host_id) == str(guest.id):
            return None, "You cannot book your own listing."

        price = BookingService.calculate_price(listing, check_in, check_out)

        booking = Booking.objects.create(
            listing=listing,
            guest=guest,
            check_in=check_in,
            check_out=check_out,
            num_guests=num_guests,
            price_per_night=price.price_per_night,
            num_nights=price.num_nights,
            subtotal=price.subtotal,
            service_fee=price.service_fee,
            cleaning_fee=price.cleaning_fee,
            total_price=price.total_price,
            status=Booking.Status.PENDING_PAYMENT,
            special_requests=special_requests,
        )

        Payment.objects.create(
            booking=booking,
            amount=price.total_price,
            currency="USD",
            status=Payment.Status.PENDING,
            payment_method=Payment.PaymentMethod.PLACEHOLDER,
        )

        return booking, None

    @staticmethod
    @transaction.atomic
    def confirm_booking(booking: Booking) -> tuple[bool, str]:
        """
        Confirm a booking after successful payment.
        This is a placeholder - will be called by payment webhook later.
        """
        if booking.status != Booking.Status.PENDING_PAYMENT:
            return False, f"Cannot confirm booking with status '{booking.status}'."

        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])

        payment = booking.payments.filter(status=Payment.Status.PENDING).first()
        if payment:
            payment.status = Payment.Status.COMPLETED
            payment.save(update_fields=["status", "updated_at"])

        return True, "Booking confirmed successfully."

    @staticmethod
    @transaction.atomic
    def cancel_booking(
        booking: Booking,
        cancelled_by: User,
        reason: str = "",
    ) -> tuple[bool, str]:
        """
        Cancel a booking.
        """
        if not booking.can_be_cancelled:
            return False, f"Cannot cancel booking with status '{booking.get_status_display()}'."

        is_host = str(booking.listing.host_id) == str(cancelled_by.id)
        is_guest = str(booking.guest_id) == str(cancelled_by.id)

        if not is_host and not is_guest:
            return False, "You don't have permission to cancel this booking."

        if is_host:
            booking.status = Booking.Status.CANCELLED_BY_HOST
        else:
            booking.status = Booking.Status.CANCELLED_BY_GUEST

        booking.cancellation_reason = reason
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=[
            "status", "cancellation_reason", "cancelled_at", "updated_at"
        ])

        pending_payment = booking.payments.filter(status=Payment.Status.PENDING).first()
        if pending_payment:
            pending_payment.status = Payment.Status.FAILED
            pending_payment.failure_reason = "Booking cancelled"
            pending_payment.save(update_fields=["status", "failure_reason", "updated_at"])

        return True, "Booking cancelled successfully."

    @staticmethod
    @transaction.atomic
    def complete_booking(booking: Booking) -> tuple[bool, str]:
        """
        Mark a booking as completed (after checkout date has passed).
        """
        if booking.status != Booking.Status.CONFIRMED:
            return False, f"Cannot complete booking with status '{booking.status}'."

        if booking.check_out > date.today():
            return False, "Cannot complete booking before checkout date."

        booking.status = Booking.Status.COMPLETED
        booking.save(update_fields=["status", "updated_at"])

        return True, "Booking marked as completed."


class PaymentService:
    """
    Placeholder payment service.
    Will be replaced with actual payment gateway integration later.
    """

    @staticmethod
    def create_payment_intent(booking: Booking) -> dict:
        """
        Placeholder: Create a payment intent.
        In real implementation, this would call Stripe/Razorpay API.
        """
        payment = booking.payments.filter(status=Payment.Status.PENDING).first()
        if not payment:
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                currency="USD",
                status=Payment.Status.PENDING,
            )

        return {
            "payment_id": str(payment.id),
            "amount": float(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "client_secret": f"placeholder_secret_{payment.id}",
        }

    @staticmethod
    def simulate_payment_success(payment_id: str) -> tuple[bool, str]:
        """
        Placeholder: Simulate a successful payment.
        For testing purposes only - remove in production.
        """
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return False, "Payment not found."

        if payment.status != Payment.Status.PENDING:
            return False, f"Payment already processed with status '{payment.status}'."

        payment.status = Payment.Status.COMPLETED
        payment.gateway_payment_id = f"simulated_{payment_id}"
        payment.save(update_fields=["status", "gateway_payment_id", "updated_at"])

        booking = payment.booking
        if booking.status == Booking.Status.PENDING_PAYMENT:
            booking.status = Booking.Status.CONFIRMED
            booking.save(update_fields=["status", "updated_at"])

        return True, "Payment successful. Booking confirmed."
