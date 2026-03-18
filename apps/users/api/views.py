import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.utils import timezone

from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import (
    ChatKeyBackupSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
    create_social_user,
)


User = get_user_model()
GOOGLE_STATE_SALT = "users.google-oauth.state"
GOOGLE_EXCHANGE_CACHE_PREFIX = "users.google-oauth.exchange"
GOOGLE_STATE_ERROR = "Unable to verify the Google sign-in request."


def _get_safe_redirect(redirect: str | None) -> str:
    if not redirect or not isinstance(redirect, str):
        return "/dashboard"
    if not redirect.startswith("/") or redirect.startswith("//") or redirect.startswith("/auth"):
        return "/dashboard"
    return redirect


def _build_auth_payload(user, request=None) -> dict[str, object]:
    refresh = RefreshToken.for_user(user)
    serializer = UserSerializer(user, context={"request": request} if request else {})
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": serializer.data,
    }


def _build_frontend_callback_url(*, redirect: str, code: str | None = None, error: str | None = None) -> str:
    params: dict[str, str] = {"redirect": redirect}
    if code:
        params["code"] = code
    if error:
        params["error"] = error
    return f"{settings.GOOGLE_OAUTH_FRONTEND_CALLBACK_URL}?{urlencode(params)}"


def _build_google_auth_url(state_token: str) -> str:
    query = urlencode(
        {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(settings.GOOGLE_OAUTH_SCOPES),
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": settings.GOOGLE_OAUTH_PROMPT,
            "state": state_token,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def _exchange_google_code_for_tokens(code: str) -> dict[str, object]:
    payload = urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise AuthenticationFailed("Google sign-in could not be completed.") from exc


def _fetch_google_userinfo(access_token: str) -> dict[str, object]:
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise AuthenticationFailed("Unable to read your Google profile.") from exc


def _build_username_from_google_profile(profile: dict[str, object]) -> str:
    full_name = str(profile.get("name") or "").strip()
    if full_name:
        return full_name
    email = str(profile.get("email") or "").strip()
    if email:
        return email.split("@", 1)[0]
    return "Google User"


def _get_or_create_google_user(profile: dict[str, object]):
    email = str(profile.get("email") or "").strip().lower()
    if not email:
        raise AuthenticationFailed("Google did not provide an email address.")
    if not profile.get("email_verified", False):
        raise AuthenticationFailed("Your Google email address must be verified.")

    existing_user = User.objects.filter(email__iexact=email).first()
    if existing_user:
        if not existing_user.is_active:
            raise AuthenticationFailed("No active account found with the given credentials")
        return existing_user

    username = _build_username_from_google_profile(profile)

    try:
        return create_social_user(
            username=username,
            email=email,
            phone_number=None,
        )
    except IntegrityError as exc:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            return user
        raise AuthenticationFailed("Unable to finish creating your account.") from exc


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

        # Validate file type (images only)
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
        if avatar_file.content_type not in allowed_types:
            return Response(
                {"detail": "Invalid file type. Only JPEG, PNG, WebP, and GIF images are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if avatar_file.size > max_size:
            return Response(
                {"detail": "File size exceeds 5MB limit. Please upload a smaller image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete old avatar if it exists
        if user.avatar:
            try:
                user.avatar.delete(save=False)
            except Exception:
                pass  # Ignore errors deleting old avatar
        
        # Assign and save - Cloudinary storage will handle the upload
        user.avatar = avatar_file
        user.save(update_fields=["avatar"])
        
        # Refresh from DB to ensure we have the latest Cloudinary URL
        user.refresh_from_db()
        
        # Debug: Log the avatar URL to verify Cloudinary is working
        if user.avatar:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Avatar uploaded - URL: {user.avatar.url}, Storage: {user.avatar.storage}")

        serializer = self.get_serializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        Remove the authenticated user's profile photo.
        """

        user = request.user
        if user.avatar:
            # This removes the file from storage and clears the field.
            user.avatar.delete(save=True)

        serializer = self.get_serializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatKeyBackupView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatKeyBackupSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(chat_key_uploaded_at=timezone.now())
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

        return _build_auth_payload(user)


class GoogleOAuthStartView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            frontend_callback_url = _build_frontend_callback_url(
                redirect=_get_safe_redirect(request.query_params.get("redirect")),
                error="Google sign-in is not configured yet.",
            )
            return HttpResponseRedirect(frontend_callback_url)

        redirect_target = _get_safe_redirect(request.query_params.get("redirect"))
        state_token = signing.dumps({"redirect": redirect_target}, salt=GOOGLE_STATE_SALT)
        return HttpResponseRedirect(_build_google_auth_url(state_token))


class GoogleOAuthCallbackView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            state_payload = signing.loads(
                request.query_params.get("state", ""),
                salt=GOOGLE_STATE_SALT,
                max_age=settings.GOOGLE_OAUTH_STATE_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            return HttpResponseRedirect(
                _build_frontend_callback_url(redirect="/dashboard", error=GOOGLE_STATE_ERROR)
            )
        except signing.SignatureExpired:
            return HttpResponseRedirect(
                _build_frontend_callback_url(
                    redirect="/dashboard",
                    error="Google sign-in took too long. Please try again.",
                )
            )

        redirect_target = _get_safe_redirect(state_payload.get("redirect"))
        oauth_error = request.query_params.get("error")
        if oauth_error:
            return HttpResponseRedirect(
                _build_frontend_callback_url(
                    redirect=redirect_target,
                    error="Google sign-in was cancelled or denied.",
                )
            )

        code = (request.query_params.get("code") or "").strip()
        if not code:
            return HttpResponseRedirect(
                _build_frontend_callback_url(
                    redirect=redirect_target,
                    error="Google did not return an authorization code.",
                )
            )

        try:
            token_data = _exchange_google_code_for_tokens(code)
            access_token = str(token_data.get("access_token") or "").strip()
            if not access_token:
                raise AuthenticationFailed("Google sign-in could not be completed.")
            profile = _fetch_google_userinfo(access_token)
            user = _get_or_create_google_user(profile)
            auth_payload = _build_auth_payload(user, request=request)
        except AuthenticationFailed as exc:
            return HttpResponseRedirect(
                _build_frontend_callback_url(redirect=redirect_target, error=str(exc.detail))
            )

        exchange_code = secrets.token_urlsafe(32)
        cache_key = f"{GOOGLE_EXCHANGE_CACHE_PREFIX}:{exchange_code}"
        cache.set(
            cache_key,
            {
                "redirect": redirect_target,
                "auth": auth_payload,
            },
            timeout=settings.GOOGLE_OAUTH_EXCHANGE_TTL_SECONDS,
        )
        return HttpResponseRedirect(
            _build_frontend_callback_url(redirect=redirect_target, code=exchange_code)
        )


class GoogleOAuthExchangeSerializer(serializers.Serializer):
    code = serializers.CharField()


class GoogleOAuthExchangeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleOAuthExchangeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        cache_key = f"{GOOGLE_EXCHANGE_CACHE_PREFIX}:{code}"
        payload = cache.get(cache_key)
        if payload is None:
            raise serializers.ValidationError("This Google sign-in link has expired. Please try again.")

        cache.delete(cache_key)
        return Response(
            {
                **payload["auth"],
                "redirect": payload["redirect"],
            },
            status=status.HTTP_200_OK,
        )

