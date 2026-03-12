from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.bookings.services import BookingService, PriceBreakdown
from apps.listings.models import Listing


class BookingConflictTests(APITestCase):
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
            title="Lake House",
            description="Quiet stay by the water.",
            location="Nainital",
            category="lakefront",
            price_per_night="6000.00",
            bedrooms=3,
            bathrooms="2.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/lake-house.jpg"],
            is_active=True,
        )
        self.client.force_authenticate(user=self.guest)
        self.existing_booking = Booking.objects.create(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=13),
            num_guests=2,
            price_per_night="6000.00",
            num_nights=3,
            subtotal="18000.00",
            service_fee="2160.00",
            cleaning_fee="250.00",
            total_price="20410.00",
            status=Booking.Status.CONFIRMED,
        )

    @patch("apps.bookings.api.views.PaymentService.create_payment_intent")
    def test_create_booking_returns_conflict_response_for_overlapping_dates(
        self,
        mock_create_payment_intent,
    ):
        response = self.client.post(
            reverse("booking-list"),
            {
                "listing_id": str(self.listing.id),
                "check_in": (date.today() + timedelta(days=11)).isoformat(),
                "check_out": (date.today() + timedelta(days=14)).isoformat(),
                "num_guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data["detail"],
            "Selected dates overlap with an existing booking. Please choose different dates.",
        )
        self.assertEqual(
            response.data["code"],
            BookingService.BOOKING_DATES_OVERLAP_CODE,
        )
        self.assertEqual(response.data["conflicts_count"], 1)
        self.assertEqual(
            response.data["conflicts"][0]["id"],
            str(self.existing_booking.id),
        )
        self.assertEqual(
            response.data["conflicts"][0]["check_in"],
            self.existing_booking.check_in.isoformat(),
        )
        self.assertEqual(
            response.data["conflicts"][0]["check_out"],
            self.existing_booking.check_out.isoformat(),
        )
        self.assertEqual(Booking.objects.count(), 1)
        mock_create_payment_intent.assert_not_called()

    @patch("apps.bookings.api.views.PaymentService.create_payment_intent")
    def test_create_booking_allows_back_to_back_dates(self, mock_create_payment_intent):
        mock_create_payment_intent.return_value = {
            "order_id": "order_456",
            "razorpay_key_id": "rzp_test_key",
            "amount": 13700.0,
            "currency": "INR",
            "payment_id": "payment_456",
        }

        response = self.client.post(
            reverse("booking-list"),
            {
                "listing_id": str(self.listing.id),
                "check_in": self.existing_booking.check_out.isoformat(),
                "check_out": (self.existing_booking.check_out + timedelta(days=2)).isoformat(),
                "num_guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 2)
        mock_create_payment_intent.assert_called_once()

    def test_check_availability_returns_conflict_ranges(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("booking-check-availability"),
            {
                "listing_id": str(self.listing.id),
                "check_in": (date.today() + timedelta(days=11)).isoformat(),
                "check_out": (date.today() + timedelta(days=14)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_available"])
        self.assertEqual(response.data["conflicts_count"], 1)
        self.assertEqual(
            response.data["conflicts"][0]["check_in"],
            self.existing_booking.check_in.isoformat(),
        )
        self.assertEqual(
            response.data["conflicts"][0]["check_out"],
            self.existing_booking.check_out.isoformat(),
        )

    @patch("apps.bookings.services.Payment.objects.create")
    @patch("apps.bookings.services.Booking.objects.create")
    @patch("apps.bookings.services.BookingService.calculate_price")
    @patch("apps.bookings.services.BookingService.check_availability")
    @patch("apps.bookings.services.Listing.objects.select_for_update")
    def test_create_booking_locks_listing_before_creating(
        self,
        mock_select_for_update,
        mock_check_availability,
        mock_calculate_price,
        mock_booking_create,
        mock_payment_create,
    ):
        locked_queryset = Mock()
        mock_select_for_update.return_value = locked_queryset
        locked_queryset.get.return_value = self.listing
        mock_check_availability.return_value = (True, [])
        mock_calculate_price.return_value = PriceBreakdown(
            price_per_night=Decimal("6000.00"),
            num_nights=2,
            subtotal=Decimal("12000.00"),
            service_fee=Decimal("1440.00"),
            cleaning_fee=Decimal("250.00"),
            total_price=Decimal("13690.00"),
        )
        mock_booking = Mock(spec=Booking)
        mock_booking_create.return_value = mock_booking

        booking, error = BookingService.create_booking(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=20),
            check_out=date.today() + timedelta(days=22),
            num_guests=2,
        )

        self.assertIs(booking, mock_booking)
        self.assertIsNone(error)
        mock_select_for_update.assert_called_once_with()
        locked_queryset.get.assert_called_once_with(pk=self.listing.pk)
        mock_check_availability.assert_called_once_with(
            listing_id=str(self.listing.id),
            check_in=date.today() + timedelta(days=20),
            check_out=date.today() + timedelta(days=22),
        )
        mock_booking_create.assert_called_once()
        mock_payment_create.assert_called_once()
