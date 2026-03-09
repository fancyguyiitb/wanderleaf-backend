import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, OperationalError, close_old_connections, connection
from django.test import TestCase, TransactionTestCase

from apps.bookings.models import Booking
from apps.bookings.services import BookingService, PriceBreakdown
from apps.listings.models import Listing
from apps.payments.models import Payment


class BookingConcurrencyServiceTests(TestCase):
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
            title="River Retreat",
            description="Quiet stay near the river.",
            location="Rishikesh",
            category="riverside",
            price_per_night="5000.00",
            bedrooms=2,
            bathrooms="1.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/river-retreat.jpg"],
            is_active=True,
        )

    @patch("apps.bookings.services.BookingService.create_booking_records")
    @patch("apps.bookings.services.BookingService.calculate_price")
    @patch("apps.bookings.services.BookingService.check_availability")
    @patch("apps.bookings.services.BookingService.lock_listing_for_booking")
    def test_create_booking_retries_once_for_retryable_db_error(
        self,
        mock_lock_listing,
        mock_check_availability,
        mock_calculate_price,
        mock_create_booking_records,
    ):
        mock_lock_listing.return_value = self.listing
        mock_check_availability.return_value = (True, [])
        mock_calculate_price.return_value = PriceBreakdown(
            price_per_night=Decimal("5000.00"),
            num_nights=2,
            subtotal=Decimal("10000.00"),
            service_fee=Decimal("1200.00"),
            cleaning_fee=Decimal("250.00"),
            total_price=Decimal("11450.00"),
        )
        created_booking = Mock(spec=Booking)
        mock_create_booking_records.side_effect = [
            OperationalError("database is locked"),
            created_booking,
        ]

        booking, error = BookingService.create_booking(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=20),
            check_out=date.today() + timedelta(days=22),
            num_guests=2,
        )

        self.assertIs(booking, created_booking)
        self.assertIsNone(error)
        self.assertEqual(mock_create_booking_records.call_count, 2)

    @patch("apps.bookings.services.BookingService.create_booking_records")
    @patch("apps.bookings.services.BookingService.calculate_price")
    @patch("apps.bookings.services.BookingService.check_availability")
    @patch("apps.bookings.services.BookingService.lock_listing_for_booking")
    def test_create_booking_translates_overlap_constraint_violation(
        self,
        mock_lock_listing,
        mock_check_availability,
        mock_calculate_price,
        mock_create_booking_records,
    ):
        mock_lock_listing.return_value = self.listing
        mock_check_availability.side_effect = [
            (True, []),
            (
                False,
                [
                    {
                        "id": self.listing.id,
                        "check_in": date.today() + timedelta(days=12),
                        "check_out": date.today() + timedelta(days=15),
                        "status": Booking.Status.CONFIRMED,
                    }
                ],
            ),
        ]
        mock_calculate_price.return_value = PriceBreakdown(
            price_per_night=Decimal("5000.00"),
            num_nights=3,
            subtotal=Decimal("15000.00"),
            service_fee=Decimal("1800.00"),
            cleaning_fee=Decimal("250.00"),
            total_price=Decimal("17050.00"),
        )
        mock_create_booking_records.side_effect = IntegrityError(
            f'violates exclusion constraint "{BookingService.OVERLAP_CONSTRAINT_NAME}"'
        )

        booking, error = BookingService.create_booking(
            listing=self.listing,
            guest=self.guest,
            check_in=date.today() + timedelta(days=12),
            check_out=date.today() + timedelta(days=16),
            num_guests=2,
        )

        self.assertIsNone(booking)
        self.assertIsInstance(error, dict)
        self.assertEqual(error["code"], BookingService.BOOKING_DATES_OVERLAP_CODE)
        self.assertEqual(error["conflicts_count"], 1)


class BookingConcurrencyTransactionTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        user_model = get_user_model()
        self.host = user_model.objects.create_user(
            email="host@example.com",
            username="Host User",
            password="testpass123",
        )
        self.guest_one = user_model.objects.create_user(
            email="guest-one@example.com",
            username="Guest One",
            password="testpass123",
        )
        self.guest_two = user_model.objects.create_user(
            email="guest-two@example.com",
            username="Guest Two",
            password="testpass123",
        )
        self.listing = Listing.objects.create(
            host=self.host,
            title="Cliffside Villa",
            description="A scenic cliffside stay.",
            location="Goa",
            category="villas",
            price_per_night="7000.00",
            bedrooms=3,
            bathrooms="2.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/cliffside-villa.jpg"],
            is_active=True,
        )

    def _run_create(self, guest_id, listing_id, start_barrier):
        close_old_connections()
        try:
            guest = get_user_model().objects.get(id=guest_id)
            listing = Listing.objects.get(id=listing_id)
            start_barrier.wait()
            return BookingService.create_booking(
                listing=listing,
                guest=guest,
                check_in=date.today() + timedelta(days=30),
                check_out=date.today() + timedelta(days=33),
                num_guests=2,
            )
        finally:
            close_old_connections()

    def test_postgres_overlap_guard_blocks_direct_overlapping_inserts(self):
        if not BookingService.supports_native_booking_overlap_guard():
            self.skipTest("Native overlap guard is only available on PostgreSQL.")

        Booking.objects.create(
            listing=self.listing,
            guest=self.guest_one,
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=13),
            num_guests=2,
            price_per_night="7000.00",
            num_nights=3,
            subtotal="21000.00",
            service_fee="2520.00",
            cleaning_fee="250.00",
            total_price="23770.00",
            status=Booking.Status.CONFIRMED,
        )

        with self.assertRaises(IntegrityError):
            Booking.objects.create(
                listing=self.listing,
                guest=self.guest_two,
                check_in=date.today() + timedelta(days=11),
                check_out=date.today() + timedelta(days=14),
                num_guests=2,
                price_per_night="7000.00",
                num_nights=3,
                subtotal="21000.00",
                service_fee="2520.00",
                cleaning_fee="250.00",
                total_price="23770.00",
                status=Booking.Status.CONFIRMED,
            )

    def test_concurrent_service_creates_allow_only_one_overlapping_booking(self):
        if not connection.features.has_select_for_update:
            self.skipTest("Row-level booking lock test requires select_for_update support.")

        start_barrier = Barrier(2)
        original_create_records = BookingService.create_booking_records

        def delayed_create_records(*args, **kwargs):
            time.sleep(0.2)
            return original_create_records(*args, **kwargs)

        with patch(
            "apps.bookings.services.BookingService.create_booking_records",
            side_effect=delayed_create_records,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        self._run_create,
                        self.guest_one.id,
                        self.listing.id,
                        start_barrier,
                    ),
                    executor.submit(
                        self._run_create,
                        self.guest_two.id,
                        self.listing.id,
                        start_barrier,
                    ),
                ]
                results = [future.result(timeout=10) for future in futures]

        successful_bookings = [booking for booking, error in results if booking is not None]
        overlap_errors = [
            error
            for booking, error in results
            if booking is None
            and isinstance(error, dict)
            and error.get("code") == BookingService.BOOKING_DATES_OVERLAP_CODE
        ]

        self.assertEqual(len(successful_bookings), 1)
        self.assertEqual(len(overlap_errors), 1)
        self.assertEqual(
            Booking.objects.filter(
                listing=self.listing,
                check_in=date.today() + timedelta(days=30),
                check_out=date.today() + timedelta(days=33),
            ).count(),
            1,
        )
        self.assertEqual(
            Payment.objects.filter(booking__listing=self.listing).count(),
            1,
        )
