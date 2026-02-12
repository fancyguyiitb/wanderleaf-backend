from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import MeView, RegisterView


urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="auth-register"),
    # JWT login / token pair
    path("login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    # Current user profile
    path("me/", MeView.as_view(), name="auth-me"),
]


