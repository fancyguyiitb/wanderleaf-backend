from channels.routing import URLRouter

from apps.messaging.routing import websocket_urlpatterns


websocket_urlpatterns = URLRouter(websocket_urlpatterns)
