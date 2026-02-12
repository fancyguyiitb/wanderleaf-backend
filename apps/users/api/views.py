from rest_framework import viewsets

from apps.users.models import User


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Placeholder read-only viewset for users.

    We will flesh this out with serializers and proper permissions later.
    """

    queryset = User.objects.all()
    serializer_class = None  # to be defined

