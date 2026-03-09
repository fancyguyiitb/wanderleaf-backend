from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.listings.models import Listing
from apps.payments.models import Payment


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@wanderleaf.com",
)
class BookingEmailNotificationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.host = user_model.objects.create_user(
            email="host@example.com",
            username="Host User",
            password="testpass123",
        )
        self.guest = user_model.objects.create_user(
            email="guest@example.com",
            username="Guest User",
            password="testpass123",
        )
        self.listing = Listing.objects.create(
            host=self.host,
            title="Forest Cabin",
            description="Quiet stay in the woods.",
            location="Manali",
            category="cabins",
            price_per_night="4500.00",
            bedrooms=2,
            bathrooms="1.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/cabin.jpg"],
            is_active=True,
        )

    def create_booking(self, *, status=Booking.Status.PENDING_PAYMENT, created_at=None):
        booking = Booking.objects.create(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            num_guests=2,
            price_per_night="4500.00",
            num_nights=3,
            subtotal="13500.00",
            service_fee="1620.00",
            cleaning_fee="250.00",
            total_price="15370.00",
            status=status,
        )
        if created_at is not None:
            Booking.objects.filter(id=booking.id).update(created_at=created_at)
            booking.refresh_from_db()
        return booking

    def create_payment(
        self,
        booking,
        *,
        status=Payment.Status.PENDING,
        gateway_order_id="order_123",
        gateway_payment_id="",
    ):
        return Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            currency="INR",
            status=status,
            payment_method=Payment.PaymentMethod.CARD,
            gateway_order_id=gateway_order_id,
            gateway_payment_id=gateway_payment_id,
        )

    @patch("apps.bookings.api.views.PaymentService.create_payment_intent")
    def test_create_booking_sends_pending_payment_emails(self, mock_create_payment_intent):
        mock_create_payment_intent.return_value = {
            "order_id": "order_123",
            "razorpay_key_id": "rzp_test_key",
            "amount": 15370.0,
            "currency": "INR",
            "payment_id": "payment_123",
        }
        self.client.force_authenticate(user=self.guest)

        response = self.client.post(
            reverse("booking-list"),
            {
                "listing_id": str(self.listing.id),
                "check_in": (date.today() + timedelta(days=7)).isoformat(),
                "check_out": (date.today() + timedelta(days=10)).isoformat(),
                "num_guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual({email.to[0] for email in mail.outbox}, {self.guest.email, self.host.email})
        self.assertIn("Booking request created", mail.outbox[0].subject + mail.outbox[1].subject)

    @patch("apps.bookings.api.views.PaymentService.verify_razorpay_payment")
    def test_verify_payment_success_sends_confirmation_emails(self, mock_verify_payment):
        booking = self.create_booking()
        payment = self.create_payment(booking)

        def mark_paid(**kwargs):
            payment.status = Payment.Status.COMPLETED
            payment.gateway_payment_id = "pay_123"
            payment.gateway_signature = "sig_123"
            payment.save(update_fields=["status", "gateway_payment_id", "gateway_signature", "updated_at"])
            booking.status = Booking.Status.CONFIRMED
            booking.save(update_fields=["status", "updated_at"])
            return True, "Payment verified. Booking confirmed."

        mock_verify_payment.side_effect = mark_paid
        self.client.force_authenticate(user=self.guest)

        response = self.client.post(
            reverse("booking-verify-payment", args=[booking.id]),
            {
                "razorpay_order_id": payment.gateway_order_id,
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "sig_123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual({email.to[0] for email in mail.outbox}, {self.guest.email, self.host.email})
        self.assertTrue(any("Booking confirmed" in email.subject for email in mail.outbox))
        self.assertTrue(any("Payment received" in email.subject for email in mail.outbox))

    @patch("apps.bookings.api.views.PaymentService.verify_razorpay_payment")
    def test_verify_payment_failure_sends_guest_failure_email(self, mock_verify_payment):
        booking = self.create_booking()
        payment = self.create_payment(booking)
        mock_verify_payment.return_value = False, "Payment verification failed."
        self.client.force_authenticate(user=self.guest)

        response = self.client.post(
            reverse("booking-verify-payment", args=[booking.id]),
            {
                "razorpay_order_id": payment.gateway_order_id,
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "sig_123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.guest.email])
        self.assertIn("Payment verification failed", mail.outbox[0].subject)

    def test_cancelling_booking_sends_guest_and_host_emails(self):
        booking = self.create_booking()
        self.create_payment(booking)
        self.client.force_authenticate(user=self.guest)

        response = self.client.post(
            reverse("booking-cancel", args=[booking.id]),
            {"reason": "Change of plans"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual({email.to[0] for email in mail.outbox}, {self.guest.email, self.host.email})
        self.assertTrue(all("Booking cancelled" in email.subject for email in mail.outbox))

    def test_expired_booking_retrieve_sends_guest_expiry_email(self):
        expired_time = timezone.now() - timedelta(minutes=16)
        booking = self.create_booking(created_at=expired_time)
        self.create_payment(booking)
        self.client.force_authenticate(user=self.guest)

        response = self.client.get(reverse("booking-detail", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.guest.email])
        self.assertIn("Payment window expired", mail.outbox[0].subject)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED_BY_GUEST)
