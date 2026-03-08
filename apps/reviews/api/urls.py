from django.urls import path

from apps.reviews.api.views import ReviewListCreateView

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="review-list-create"),
]

