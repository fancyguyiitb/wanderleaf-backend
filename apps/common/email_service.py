import logging
from collections.abc import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


class NotificationEmailService:
    """Sends booking and payment lifecycle emails to guests and hosts."""

    @classmethod
    def send_booking_created(cls, booking) -> None:
        cls._send_event_email(
            booking=booking,
            event_name="booking_created",
            recipient_roles=("guest", "host"),
        )

    @classmethod
    def send_booking_cancelled(
        cls,
        booking,
        cancelled_by,
        refund_code: str | None = None,
    ) -> None:
        cancelled_by_role = "host" if str(booking.listing.host_id) == str(cancelled_by.id) else "guest"
        cls._send_event_email(
            booking=booking,
            event_name="booking_cancelled",
            recipient_roles=("guest", "host"),
            extra_context={
                "cancelled_by_role": cancelled_by_role,
                "refund_code": refund_code,
            },
        )

    @classmethod
    def send_payment_success(cls, booking) -> None:
        cls._send_event_email(
            booking=booking,
            event_name="payment_success",
            recipient_roles=("guest", "host"),
        )

    @classmethod
    def send_payment_failed(cls, booking, reason: str) -> None:
        cls._send_event_email(
            booking=booking,
            event_name="payment_failed",
            recipient_roles=("guest",),
            extra_context={"failure_reason": reason},
        )

    @classmethod
    def _send_event_email(
        cls,
        booking,
        event_name: str,
        recipient_roles: Iterable[str],
        extra_context: dict | None = None,
    ) -> None:
        if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True):
            return
        if not cls._email_backend_is_available():
            logger.info("Skipping %s email because email is not configured.", event_name)
            return

        context = cls._build_context(booking, extra_context or {})
        for recipient_role in recipient_roles:
            recipient = booking.guest if recipient_role == "guest" else booking.listing.host
            recipient_email = getattr(recipient, "email", "")
            if not recipient_email:
                logger.warning(
                    "Skipping %s email for booking %s because %s has no email address.",
                    event_name,
                    booking.id,
                    recipient_role,
                )
                continue

            role_context = {
                **context,
                "recipient": recipient,
                "recipient_role": recipient_role,
            }
            subject = cls._build_subject(
                event_name=event_name,
                recipient_role=recipient_role,
                booking=booking,
                extra_context=extra_context or {},
            )
            cls._send_rendered_email(
                to_email=recipient_email,
                subject=subject,
                text_template=f"emails/{event_name}.txt",
                html_template=f"emails/{event_name}.html",
                context=role_context,
            )

    @staticmethod
    def _build_context(booking, extra_context: dict) -> dict:
        refund_code = extra_context.get("refund_code")
        failure_reason = extra_context.get("failure_reason")

        return {
            "booking": booking,
            "listing": booking.listing,
            "guest": booking.guest,
            "host": booking.listing.host,
            "site_name": "Wanderleaf",
            "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", ""),
            "refund_code": refund_code,
            "refund_message": NotificationEmailService._refund_message(refund_code),
            "cancelled_by_role": extra_context.get("cancelled_by_role"),
            "failure_reason": failure_reason,
            "failure_message": NotificationEmailService._failure_message(failure_reason),
        }

    @staticmethod
    def _send_rendered_email(
        *,
        to_email: str,
        subject: str,
        text_template: str,
        html_template: str,
        context: dict,
    ) -> None:
        try:
            text_body = render_to_string(text_template, context)
            html_body = render_to_string(html_template, context)
            message = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            message.attach_alternative(html_body, "text/html")
            message.send(fail_silently=False)
        except Exception:
            logger.exception(
                "Failed to send notification email '%s' for booking %s to %s.",
                text_template,
                context["booking"].id,
                to_email,
            )

    @staticmethod
    def _email_backend_is_available() -> bool:
        backend = getattr(settings, "EMAIL_BACKEND", "")
        if not backend:
            return False

        if backend == "django.core.mail.backends.smtp.EmailBackend":
            return bool(getattr(settings, "EMAIL_HOST", ""))

        return True

    @staticmethod
    def _build_subject(
        *,
        event_name: str,
        recipient_role: str,
        booking,
        extra_context: dict,
    ) -> str:
        listing_title = booking.listing.title
        if event_name == "booking_created":
            if recipient_role == "guest":
                return f"Booking request created for {listing_title}"
            return f"New booking request for {listing_title}"

        if event_name == "booking_cancelled":
            if recipient_role == "guest":
                return f"Booking cancelled for {listing_title}"
            return f"Booking cancelled on {listing_title}"

        if event_name == "payment_success":
            if recipient_role == "guest":
                return f"Booking confirmed for {listing_title}"
            return f"Payment received for {listing_title}"

        if event_name == "payment_failed":
            reason = extra_context.get("failure_reason")
            if reason == "expired":
                return f"Payment window expired for {listing_title}"
            return f"Payment verification failed for {listing_title}"

        return f"Booking update for {listing_title}"

    @staticmethod
    def _refund_message(refund_code: str | None) -> str:
        messages = {
            "refund_initiated": "Your refund has been initiated and should reflect within 5-7 working days.",
            "refund_failed": "We could not process the refund automatically. Please contact support with your booking ID.",
            "no_refund_needed": "No refund was needed because the payment was not captured.",
            None: "",
        }
        return messages.get(refund_code, "")

    @staticmethod
    def _failure_message(reason: str | None) -> str:
        messages = {
            "expired": "Your 15-minute payment window expired, so the booking was cancelled automatically.",
            "verification_failed": "We could not verify your payment. If you were charged, please contact support with your booking ID.",
            None: "",
        }
        return messages.get(reason, "Your payment could not be completed.")
