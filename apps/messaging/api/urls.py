from django.urls import path

from apps.messaging.api.views import (
    BookingConversationView,
    ConversationAttachmentUploadView,
    InboxListView,
    UnreadCountView,
)

urlpatterns = [
    path("inbox/", InboxListView.as_view(), name="inbox-list"),
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
    path(
        "bookings/<uuid:booking_id>/conversation/",
        BookingConversationView.as_view(),
        name="booking-conversation",
    ),
    path(
        "conversations/<uuid:conversation_id>/attachments/",
        ConversationAttachmentUploadView.as_view(),
        name="conversation-attachments",
    ),
]

