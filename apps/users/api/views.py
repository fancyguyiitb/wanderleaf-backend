from django.contrib.auth import get_user_model

from rest_framework import generics, permissions

from apps.users.serializers import RegisterSerializer, UserSerializer


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Register a new user.

    Request body:
    {
      "username": "yourname",
      "email": "you@example.com",
      "password": "yourpassword"
    }
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MeView(generics.RetrieveAPIView):
    """
    Return the currently authenticated user's profile.
    """

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


