from django.urls import re_path

from apps.messaging.consumers import BookingChatConsumer, NotificationConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/messaging/notifications/$",
        NotificationConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/messaging/conversations/(?P<conversation_id>[^/]+)/$",
        BookingChatConsumer.as_asgi(),
    ),
]
