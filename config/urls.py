from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.users.api.urls")),
    path("api/v1/listings/", include("apps.listings.api.urls")),
    path("api/v1/bookings/", include("apps.bookings.api.urls")),
    path("api/v1/payments/", include("apps.payments.api.urls")),
    path("api/v1/reviews/", include("apps.reviews.api.urls")),
    path("api/v1/messaging/", include("apps.messaging.api.urls")),
]

