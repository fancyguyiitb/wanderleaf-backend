from rest_framework import viewsets

from apps.bookings.models import Booking


class BookingViewSet(viewsets.ModelViewSet):
    """
    Placeholder ViewSet for bookings.
    """

    queryset = Booking.objects.all()
    serializer_class = None  # to be defined

