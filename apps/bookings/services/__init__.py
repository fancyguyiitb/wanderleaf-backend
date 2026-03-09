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

    BOOKING_DATES_OVERLAP_CODE = "booking_dates_overlap"

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
    def serialize_conflicts(conflicts: list[dict]) -> list[dict[str, str]]:
        """Normalize conflicting booking ranges for API responses."""
        return [
            {
                "id": str(conflict["id"]),
                "check_in": conflict["check_in"].isoformat(),
                "check_out": conflict["check_out"].isoformat(),
                "status": str(conflict["status"]),
            }
            for conflict in conflicts
        ]

    @staticmethod
    def build_overlap_error(conflicts: list[dict]) -> dict[str, object]:
        """Build a consistent overlap error payload for API clients."""
        serialized_conflicts = BookingService.serialize_conflicts(conflicts)
        return {
            "detail": (
                "Selected dates overlap with an existing booking. "
                "Please choose different dates."
            ),
            "code": BookingService.BOOKING_DATES_OVERLAP_CODE,
            "conflicts_count": len(serialized_conflicts),
            "conflicts": serialized_conflicts,
        }

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
    ) -> tuple[Booking | None, str | dict[str, object] | None]:
        """
        Create a new booking with all validations.
        
        Returns:
            Tuple of (booking, error_message)
        """
        # Lock the listing row when the database supports it so concurrent
        # booking attempts for the same property are serialized.
        listing = Listing.objects.select_for_update().get(pk=listing.pk)

        is_available, conflicts = BookingService.check_availability(
            listing_id=str(listing.id),
            check_in=check_in,
            check_out=check_out,
        )

        if not is_available:
            return None, BookingService.build_overlap_error(conflicts)

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
    ) -> tuple[bool, str, str | None]:
        """
        Cancel a booking. Processes refund when applicable (CONFIRMED bookings).

        Returns:
            Tuple of (success, message, refund_code).
            refund_code: None | "refund_initiated" | "refund_failed" | "no_refund_needed"
        """
        if not booking.can_be_cancelled:
            return False, f"Cannot cancel booking with status '{booking.get_status_display()}'.", None

        is_host = str(booking.listing.host_id) == str(cancelled_by.id)
        is_guest = str(booking.guest_id) == str(cancelled_by.id)

        if not is_host and not is_guest:
            return False, "You don't have permission to cancel this booking.", None

        was_pending_payment = booking.status == Booking.Status.PENDING_PAYMENT
        if is_host:
            booking.status = Booking.Status.CANCELLED_BY_HOST
        else:
            booking.status = Booking.Status.CANCELLED_BY_GUEST

        booking.cancellation_reason = reason
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=[
            "status", "cancellation_reason", "cancelled_at", "updated_at"
        ])

        refund_code: str | None = None

        if was_pending_payment:
            # Payment was never captured — mark as failed, no Razorpay refund
            pending_payment = booking.payments.filter(status=Payment.Status.PENDING).first()
            if pending_payment:
                pending_payment.status = Payment.Status.FAILED
                pending_payment.failure_reason = "Booking cancelled"
                pending_payment.save(update_fields=["status", "failure_reason", "updated_at"])
            refund_code = "no_refund_needed"
            return True, "Booking cancelled successfully.", refund_code

        # CONFIRMED booking — payment was captured, initiate Razorpay refund
        completed_payment = booking.payments.filter(
            status=Payment.Status.COMPLETED,
            gateway_payment_id__isnull=False,
        ).exclude(gateway_payment_id="").first()

        if not completed_payment:
            # Edge case: CONFIRMED but no gateway_payment_id (shouldn't happen)
            refund_code = "refund_failed"
            return (
                True,
                "Booking cancelled. Refund could not be processed automatically. Please contact support with booking ID.",
                refund_code,
            )

        success, msg, _ = PaymentService.create_razorpay_refund(
            completed_payment,
            notes={
                "booking_id": str(booking.id),
                "cancelled_by": "host" if is_host else "guest",
                "reason": reason[:200] if reason else "",
            },
        )

        if success:
            refund_code = "refund_initiated"
            return True, "Booking cancelled. Refund has been initiated and will reflect in 5–7 working days.", refund_code

        refund_code = "refund_failed"
        return (
            True,
            f"Booking cancelled. Refund could not be processed: {msg} Please contact support with booking ID.",
            refund_code,
        )

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
        # If verification failed, money may have been charged; do not auto-cancel.
        if getattr(booking, "payment_retry_disallowed", False):
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
        if getattr(booking, "payment_retry_disallowed", False):
            return 0
        elapsed = (timezone.now() - booking.created_at).total_seconds()
        remaining = int(PAYMENT_WINDOW_SECONDS - elapsed)
        return max(0, remaining)

    @staticmethod
    def mark_payment_retry_disallowed(booking: Booking) -> None:
        """Call when verify-payment fails (money may have been charged)."""
        booking.payment_retry_disallowed = True
        booking.save(update_fields=["payment_retry_disallowed", "updated_at"])


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

        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])

        return True, "Payment verified. Booking confirmed."

    @staticmethod
    def create_razorpay_refund(
        payment: Payment,
        amount: Decimal | None = None,
        notes: dict | None = None,
    ) -> tuple[bool, str, Decimal]:
        """
        Create a Razorpay refund for a completed payment.

        Args:
            payment: Payment record with status=COMPLETED and gateway_payment_id set.
            amount: Refund amount (default: full amount). Must be <= payment.amount.
            notes: Optional notes for Razorpay (e.g. {"reason": "booking_cancelled"}).

        Returns:
            Tuple of (success, message, refund_amount).
            On success: refund_amount is the amount refunded.
            On failure: refund_amount is Decimal("0").
        """
        from decimal import Decimal as D

        key_id = getattr(settings, "RZP_TEST_KEY_ID", None) or os.getenv("RZP_TEST_KEY_ID")
        key_secret = getattr(settings, "RZP_TEST_KEY_SECRET", None) or os.getenv("RZP_TEST_KEY_SECRET")
        if not key_id or not key_secret:
            return False, "Payment gateway not configured. Refund could not be processed.", D("0")

        if not payment.can_be_refunded:
            if payment.status != Payment.Status.COMPLETED:
                return False, f"Cannot refund payment with status '{payment.status}'.", D("0")
            if payment.refund_amount >= payment.amount:
                return False, "Payment has already been fully refunded.", D("0")

        if not payment.gateway_payment_id:
            return False, "No gateway payment ID. Refund must be processed manually.", D("0")

        refund_amount = amount if amount is not None else payment.amount - payment.refund_amount
        refund_amount = min(refund_amount, payment.amount - payment.refund_amount)
        if refund_amount <= 0:
            return False, "No amount remaining to refund.", D("0")

        # INR: amount in paise
        amount_paise = int(Decimal(str(refund_amount)) * 100)
        if amount_paise < 100:
            return False, "Refund amount must be at least ₹1.00.", D("0")

        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
        except ImportError:
            return False, "Payment gateway not available.", D("0")

        refund_data = {
            "amount": amount_paise,
            "notes": notes or {},
        }

        try:
            refund = client.payment.refund(
                payment.gateway_payment_id,
                refund_data,
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "fully refunded" in err_msg or "already refunded" in err_msg:
                return False, "Payment has already been fully refunded.", D("0")
            if "greater than" in err_msg or "amount captured" in err_msg:
                return False, "Refund amount exceeds captured amount.", D("0")
            if "6 months" in err_msg or "too old" in err_msg:
                return False, "Refund not possible for payments older than 6 months.", D("0")
            return False, f"Refund failed: {str(e)}", D("0")

        gateway_refund_id = refund.get("id", "")
        payment.refund_amount += refund_amount
        payment.refunded_at = timezone.now()
        payment.gateway_refund_id = gateway_refund_id or payment.gateway_refund_id
        payment.status = (
            Payment.Status.REFUNDED
            if payment.refund_amount >= payment.amount
            else Payment.Status.PARTIALLY_REFUNDED
        )
        payment.save(update_fields=[
            "refund_amount", "refunded_at", "gateway_refund_id", "status", "updated_at"
        ])

        return True, "Refund initiated successfully.", refund_amount
