import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.bookings.models import Booking
from apps.listings.models import Listing
from apps.payments.models import Payment
from apps.users.models import User


SERVICE_FEE_PERCENTAGE = Decimal("0.12")  # 12% service fee
CLEANING_FEE_DEFAULT = Decimal("250.00")  # Default cleaning fee (INR)
PAYMENT_WINDOW_SECONDS = 15 * 60  # 15 minutes - non-overridable


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
            currency="INR",
            status=Payment.Status.PENDING,
            payment_method=Payment.PaymentMethod.CARD,
        )

        return booking, None

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

    @staticmethod
    @transaction.atomic
    def check_and_cancel_expired(booking: Booking) -> bool:
        """
        If booking is PENDING_PAYMENT and created more than 15 minutes ago,
        cancel it with reason and return True. Otherwise return False.
        """
        if booking.status != Booking.Status.PENDING_PAYMENT:
            return False
        elapsed = (timezone.now() - booking.created_at).total_seconds()
        if elapsed < PAYMENT_WINDOW_SECONDS:
            return False
        reason = f"Payment window expired (15 minutes). Dates freed at {timezone.now().isoformat()}."
        BookingService.cancel_booking(
            booking=booking,
            cancelled_by=booking.guest,
            reason=reason,
        )
        return True

    @staticmethod
    def get_seconds_until_payment_expiry(booking: Booking) -> int:
        """Returns seconds remaining for payment, or 0 if expired/inapplicable."""
        if booking.status != Booking.Status.PENDING_PAYMENT:
            return 0
        elapsed = (timezone.now() - booking.created_at).total_seconds()
        remaining = int(PAYMENT_WINDOW_SECONDS - elapsed)
        return max(0, remaining)

    @staticmethod
    def mark_payment_retry_disallowed(booking: Booking) -> None:
        """Call when verify-payment fails (money may have been charged)."""
        booking.payment_retry_disallowed = True
        booking.save(update_fields=["payment_retry_disallowed", "updated_at"])

    @staticmethod
    def schedule_payment_expiry_timer(booking: Booking) -> bool:
        """
        Schedule an async timer to cancel this PENDING_PAYMENT booking after 15 minutes.
        Returns True if scheduled, False if Celery is unavailable (retrieve() will still cancel on expiry).
        """
        from apps.bookings.tasks import cancel_expired_pending_booking

        try:
            result = cancel_expired_pending_booking.apply_async(
                args=[str(booking.id)],
                countdown=PAYMENT_WINDOW_SECONDS,
            )
            booking.payment_expiry_task_id = result.id
            booking.save(update_fields=["payment_expiry_task_id", "updated_at"])
            return True
        except Exception:
            return False

    @staticmethod
    def cancel_payment_expiry_timer(booking: Booking) -> None:
        """Revoke the payment expiry timer when booking is confirmed."""
        task_id = getattr(booking, "payment_expiry_task_id", None) or ""
        if not task_id:
            return
        try:
            from celery import current_app

            current_app.control.revoke(task_id)
        except Exception:
            pass


class PaymentService:
    """
    Razorpay payment service for booking payments.
    Uses Razorpay Standard Checkout (official Python SDK).
    Test mode uses INR per Razorpay docs.
    """

    @staticmethod
    def create_razorpay_order(booking: Booking) -> dict | None:
        """
        Create a Razorpay order for the booking.
        Returns order details for frontend Checkout, or None if Razorpay is not configured.
        Uses INR (paise) per official Razorpay test mode docs.
        """
        key_id = getattr(settings, "RZP_TEST_KEY_ID", None) or os.getenv("RZP_TEST_KEY_ID")
        key_secret = getattr(settings, "RZP_TEST_KEY_SECRET", None) or os.getenv("RZP_TEST_KEY_SECRET")
        if not key_id or not key_secret:
            return None

        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
        except ImportError:
            return None

        payment = booking.payments.filter(status=Payment.Status.PENDING).first()
        if not payment:
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                currency="INR",
                status=Payment.Status.PENDING,
                payment_method=Payment.PaymentMethod.CARD,
            )
        else:
            payment.currency = "INR"
            payment.payment_method = Payment.PaymentMethod.CARD
            payment.save(update_fields=["currency", "payment_method", "updated_at"])

        # INR: amount in paise (1 INR = 100 paise). Min 100 paise = ₹1.00
        amount_paise = int(Decimal(str(booking.total_price)) * 100)
        if amount_paise < 100:
            amount_paise = 100

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": str(booking.id).replace("-", "")[:40],
            "notes": {
                "booking_id": str(booking.id),
                "payment_id": str(payment.id),
            },
        }
        try:
            order = client.order.create(data=order_data)
        except Exception:
            return None
        payment.gateway_order_id = order["id"]
        payment.save(update_fields=["gateway_order_id", "updated_at"])

        return {
            "order_id": order["id"],
            "razorpay_key_id": key_id,
            "amount": float(booking.total_price),
            "currency": "INR",
            "payment_id": str(payment.id),
        }

    @staticmethod
    def create_payment_intent(booking: Booking) -> dict | None:
        """
        Create a Razorpay order for the booking.
        Returns payment info for frontend including order_id and razorpay_key_id.
        Returns None if Razorpay is not configured or order creation fails.
        """
        return PaymentService.create_razorpay_order(booking)

    @staticmethod
    def verify_razorpay_payment(
        booking_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> tuple[bool, str]:
        """
        Verify Razorpay payment signature and confirm the booking.
        Uses official razorpay.Client.utility.verify_payment_signature.
        """
        key_secret = getattr(settings, "RZP_TEST_KEY_SECRET", None) or os.getenv("RZP_TEST_KEY_SECRET")
        if not key_secret:
            return False, "Payment gateway not configured."

        try:
            import razorpay
            key_id = getattr(settings, "RZP_TEST_KEY_ID", None) or os.getenv("RZP_TEST_KEY_ID")
            client = razorpay.Client(auth=(key_id, key_secret))
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except ImportError:
            return False, "Payment gateway not available."
        except Exception as e:
            return False, f"Payment verification failed: {str(e)}"

        try:
            booking = Booking.objects.get(id=booking_id, status=Booking.Status.PENDING_PAYMENT)
        except Booking.DoesNotExist:
            return False, "Booking not found or already processed."

        payment = booking.payments.filter(
            gateway_order_id=razorpay_order_id,
            status=Payment.Status.PENDING,
        ).first()
        if not payment:
            return False, "Payment record not found."

        payment.status = Payment.Status.COMPLETED
        payment.gateway_payment_id = razorpay_payment_id
        payment.gateway_signature = razorpay_signature
        payment.save(update_fields=["status", "gateway_payment_id", "gateway_signature", "updated_at"])

        BookingService.cancel_payment_expiry_timer(booking)

        booking.status = Booking.Status.CONFIRMED
        booking.payment_expiry_task_id = ""
        booking.save(update_fields=["status", "payment_expiry_task_id", "updated_at"])

        return True, "Payment verified. Booking confirmed."
