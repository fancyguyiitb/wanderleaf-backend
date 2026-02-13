from django.contrib.auth import get_user_model

from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer


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


class MeView(generics.RetrieveUpdateAPIView):
    """
    Get or update the currently authenticated user's profile.

    - GET        /api/v1/auth/me/       -> current user data
    - PATCH/PUT  /api/v1/auth/me/       -> update provided fields only
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        # Use a different serializer for updates so fields are optional.
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        # Always treat updates as partial so only provided fields are required.
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


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

