from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    EmailOrUsernameTokenObtainPairSerializer,
    MeView,
    RegisterView,
)
from rest_framework_simplejwt.views import TokenObtainPairView


class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint that accepts either email or username as the identifier.
    """

    serializer_class = EmailOrUsernameTokenObtainPairSerializer


urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="auth-register"),
    # JWT login / token pair
    path("login/", EmailOrUsernameTokenObtainPairView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    # Current user profile
    path("me/", MeView.as_view(), name="auth-me"),
]


