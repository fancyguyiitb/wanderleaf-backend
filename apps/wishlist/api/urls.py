from django.urls import path

from . import views

urlpatterns = [
    path("", views.wishlist_list),
    path("<uuid:listing_id>/", views.wishlist_toggle),
]
