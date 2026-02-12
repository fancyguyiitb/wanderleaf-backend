from rest_framework import viewsets

from apps.reviews.models import Review


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Placeholder ViewSet for reviews.
    """

    queryset = Review.objects.all()
    serializer_class = None  # to be defined

