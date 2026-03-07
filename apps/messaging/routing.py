from django.urls import re_path

from apps.messaging.consumers import BookingChatConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/messaging/conversations/(?P<conversation_id>[^/]+)/$",
        BookingChatConsumer.as_asgi(),
    ),
]
