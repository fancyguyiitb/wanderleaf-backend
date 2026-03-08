from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.listings.models import Listing


class BookingSelfBookingTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.host = user_model.objects.create_user(
            email="host@example.com",
            username="Host User",
            password="testpass123",
        )
        self.listing = Listing.objects.create(
            host=self.host,
            title="Owner's Cabin",
            description="A quiet forest stay.",
            location="Shimla",
            category="cabins",
            price_per_night="4500.00",
            bedrooms=2,
            bathrooms="1.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/cabin.jpg"],
            is_active=True,
        )
        self.client.force_authenticate(user=self.host)

    def test_host_cannot_create_booking_for_own_listing(self):
        payload = {
            "listing_id": str(self.listing.id),
            "check_in": (date.today() + timedelta(days=7)).isoformat(),
            "check_out": (date.today() + timedelta(days=9)).isoformat(),
            "num_guests": 2,
        }

        response = self.client.post(reverse("booking-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(
            response.data,
            {"listing_id": ["You cannot book your own listing."]},
        )
