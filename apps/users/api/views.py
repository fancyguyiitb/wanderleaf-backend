from django.contrib.auth import get_user_model

from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
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


class AvatarUploadView(generics.GenericAPIView):
    """
    Upload or replace the authenticated user's profile photo.

    Endpoint:
      POST /api/v1/auth/me/avatar/

    Request (multipart/form-data):
      avatar: <image file>

    Response: updated user payload (same as /api/v1/auth/me/)
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        avatar_file = request.FILES.get("avatar")

        if not avatar_file:
            return Response(
                {"detail": "No avatar file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.avatar = avatar_file
        user.save(update_fields=["avatar"])

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        Remove the authenticated user's profile photo.
        """

        user = request.user
        if user.avatar:
            # This removes the file from storage and clears the field.
            user.avatar.delete(save=True)

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

