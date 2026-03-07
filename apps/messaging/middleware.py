from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


User = get_user_model()


@database_sync_to_async
def _get_user_from_token(token: str):
    try:
        validated_token = AccessToken(token)
        user_id = validated_token.get("user_id")
        if not user_id:
            return None
        return User.objects.filter(id=user_id, is_active=True).first()
    except (InvalidToken, TokenError):
        return None


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user_from_token(token) if token else None
        return await super().__call__(scope, receive, send)
