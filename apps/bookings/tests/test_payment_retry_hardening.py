import sys
import types
from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.bookings.services import PaymentService
from apps.listings.models import Listing
from apps.payments.models import Payment


@override_settings(
    RZP_TEST_KEY_ID="rzp_test_key",
    RZP_TEST_KEY_SECRET="rzp_test_secret",
)
class PaymentRetryHardeningTests(APITestCase):
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
            title="City Loft",
            description="Central apartment stay.",
            location="Mumbai",
            category="apartments",
            price_per_night="6500.00",
            bedrooms=2,
            bathrooms="1.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/loft.jpg"],
            is_active=True,
        )

    def create_pending_booking(self):
        booking = Booking.objects.create(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            num_guests=2,
            price_per_night="6500.00",
            num_nights=3,
            subtotal="19500.00",
            service_fee="2340.00",
            cleaning_fee="250.00",
            total_price="22090.00",
            status=Booking.Status.PENDING_PAYMENT,
        )
        Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            currency="INR",
            status=Payment.Status.PENDING,
            payment_method=Payment.PaymentMethod.CARD,
        )
        return booking

    @patch("apps.bookings.services.time.sleep", return_value=None)
    def test_create_payment_intent_retries_transient_gateway_failure(self, _mock_sleep):
        booking = self.create_pending_booking()
        order_create = Mock(side_effect=[
            Exception("gateway timeout"),
            {"id": "order_retry_success"},
        ])
        razorpay_module = types.SimpleNamespace(
            Client=Mock(return_value=types.SimpleNamespace(order=types.SimpleNamespace(create=order_create)))
        )

        with patch.dict(sys.modules, {"razorpay": razorpay_module}):
            payment_info = PaymentService.create_payment_intent(
                booking,
                idempotency_key="payment_retry_key_1",
            )

        self.assertIsNotNone(payment_info)
        self.assertEqual(payment_info["order_id"], "order_retry_success")
        self.assertEqual(order_create.call_count, 2)

    def test_create_payment_intent_reuses_existing_order_for_same_idempotency_key(self):
        booking = self.create_pending_booking()
        payment = booking.payments.first()
        payment.request_idempotency_key = "payment_retry_key_2"
        payment.gateway_order_id = "order_existing"
        payment.save(update_fields=["request_idempotency_key", "gateway_order_id", "updated_at"])

        client_mock = types.SimpleNamespace(order=types.SimpleNamespace(create=Mock()))
        razorpay_module = types.SimpleNamespace(Client=Mock(return_value=client_mock))

        with patch.dict(sys.modules, {"razorpay": razorpay_module}):
            payment_info = PaymentService.create_payment_intent(
                booking,
                idempotency_key="payment_retry_key_2",
            )

        self.assertIsNotNone(payment_info)
        self.assertEqual(payment_info["order_id"], "order_existing")
        client_mock.order.create.assert_not_called()

    @patch("apps.bookings.api.views.PaymentService.create_payment_intent")
    def test_create_booking_is_idempotent_for_same_header_key(self, mock_create_payment_intent):
        self.client.force_authenticate(user=self.guest)
        mock_create_payment_intent.return_value = {
            "order_id": "order_same",
            "razorpay_key_id": "rzp_test_key",
            "amount": 22090.0,
            "currency": "INR",
            "payment_id": "payment_same",
        }
        payload = {
            "listing_id": str(self.listing.id),
            "check_in": (date.today() + timedelta(days=7)).isoformat(),
            "check_out": (date.today() + timedelta(days=10)).isoformat(),
            "num_guests": 2,
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "booking_create_key_1"}

        first_response = self.client.post(
            reverse("booking-list"),
            payload,
            format="json",
            **headers,
        )
        second_response = self.client.post(
            reverse("booking-list"),
            payload,
            format="json",
            **headers,
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(first_response.data["booking"]["id"], second_response.data["booking"]["id"])

    def test_retry_payment_reuses_existing_order_for_same_idempotency_key(self):
        booking = self.create_pending_booking()
        payment = booking.payments.first()
        payment.request_idempotency_key = "retry_payment_key_1"
        payment.gateway_order_id = "order_retry_existing"
        payment.save(update_fields=["request_idempotency_key", "gateway_order_id", "updated_at"])
        self.client.force_authenticate(user=self.guest)

        client_mock = types.SimpleNamespace(order=types.SimpleNamespace(create=Mock()))
        razorpay_module = types.SimpleNamespace(Client=Mock(return_value=client_mock))

        with patch.dict(sys.modules, {"razorpay": razorpay_module}):
            response = self.client.post(
                reverse("booking-retry-payment", args=[booking.id]),
                format="json",
                HTTP_IDEMPOTENCY_KEY="retry_payment_key_1",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_id"], "order_retry_existing")
        client_mock.order.create.assert_not_called()


@override_settings(
    RZP_TEST_KEY_ID="rzp_test_key",
    RZP_TEST_KEY_SECRET="rzp_test_secret",
)
class PaymentVerificationIdempotencyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.host = user_model.objects.create_user(
            email="host2@example.com",
            username="Host User 2",
            password="testpass123",
        )
        self.guest = user_model.objects.create_user(
            email="guest2@example.com",
            username="Guest User 2",
            password="testpass123",
        )
        self.listing = Listing.objects.create(
            host=self.host,
            title="Beach House",
            description="Coastal getaway.",
            location="Goa",
            category="beachfront",
            price_per_night="8000.00",
            bedrooms=3,
            bathrooms="2.0",
            max_guests=5,
            amenities=["WiFi"],
            images=["https://example.com/beach-house.jpg"],
            is_active=True,
        )

    def test_verify_payment_is_idempotent_after_success(self):
        booking = Booking.objects.create(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=9),
            check_out=date.today() + timedelta(days=12),
            num_guests=2,
            price_per_night="8000.00",
            num_nights=3,
            subtotal="24000.00",
            service_fee="2880.00",
            cleaning_fee="250.00",
            total_price="27130.00",
            status=Booking.Status.CONFIRMED,
        )
        Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            currency="INR",
            status=Payment.Status.COMPLETED,
            payment_method=Payment.PaymentMethod.CARD,
            gateway_order_id="order_verified",
            gateway_payment_id="pay_verified",
            gateway_signature="sig_verified",
        )

        razorpay_module = types.SimpleNamespace(
            Client=Mock(
                return_value=types.SimpleNamespace(
                    utility=types.SimpleNamespace(verify_payment_signature=Mock())
                )
            )
        )

        with patch.dict(sys.modules, {"razorpay": razorpay_module}):
            success, message = PaymentService.verify_razorpay_payment(
                booking_id=str(booking.id),
                razorpay_order_id="order_verified",
                razorpay_payment_id="pay_verified",
                razorpay_signature="sig_verified",
            )

        self.assertTrue(success)
        self.assertEqual(message, "Payment already verified. Booking confirmed.")
