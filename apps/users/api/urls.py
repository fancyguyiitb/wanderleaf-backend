from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

from .views import (
    AvatarUploadView,
    ChatKeyBackupView,
    EmailOrUsernameTokenObtainPairSerializer,
    GoogleOAuthCallbackView,
    GoogleOAuthExchangeView,
    GoogleOAuthStartView,
    MeView,
    RegisterView,
)


class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint that accepts email + password.
    """

    serializer_class = EmailOrUsernameTokenObtainPairSerializer


urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="auth-register"),
    # JWT login / token pair
    path("login/", EmailOrUsernameTokenObtainPairView.as_view(), name="auth-login"),
    path("google/start/", GoogleOAuthStartView.as_view(), name="auth-google-start"),
    path("google/callback/", GoogleOAuthCallbackView.as_view(), name="auth-google-callback"),
    path("google/exchange/", GoogleOAuthExchangeView.as_view(), name="auth-google-exchange"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    # Current user profile
    path("me/", MeView.as_view(), name="auth-me"),
    path("me/avatar/", AvatarUploadView.as_view(), name="auth-me-avatar"),
    path("me/chat-key/", ChatKeyBackupView.as_view(), name="auth-me-chat-key"),
]


