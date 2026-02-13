from django.contrib.auth import get_user_model

from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

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


class EmailOrUsernameTokenObtainPairSerializer(serializers.Serializer):
    """
    Email-only login using SimpleJWT.

    Expected payload:
    {
      "email": "you@example.com",
      "password": "yourpassword"
    }
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        # Look up user strictly by email (case-insensitive)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None

        if user is None or not user.check_password(password) or not user.is_active:
            # Do not leak which part was wrong
            raise AuthenticationFailed(
                "No active account found with the given credentials", code="authorization"
            )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }

