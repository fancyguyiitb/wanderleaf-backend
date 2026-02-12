from rest_framework import viewsets

from apps.payments.models import Payment


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Placeholder ViewSet for payments.
    """

    queryset = Payment.objects.all()
    serializer_class = None  # to be defined

