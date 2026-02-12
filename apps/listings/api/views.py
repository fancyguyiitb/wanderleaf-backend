from rest_framework import viewsets

from apps.listings.models import Listing


class ListingViewSet(viewsets.ModelViewSet):
    """
    Placeholder ViewSet for listings.
    """

    queryset = Listing.objects.all()
    serializer_class = None  # to be defined

