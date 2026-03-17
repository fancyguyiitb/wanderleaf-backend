from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
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


def _get_header(scope, header_name: str) -> str | None:
    expected_name = header_name.lower().encode("utf-8")
    for name, value in scope.get("headers", []):
        if name == expected_name:
            return value.decode("utf-8")
    return None


def _extract_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _extract_token_from_subprotocols(scope) -> tuple[str | None, str | None]:
    subprotocols = scope.get("subprotocols") or []
    for index, value in enumerate(subprotocols[:-1]):
        if isinstance(value, str) and value.lower() == "bearer":
            token = subprotocols[index + 1]
            if isinstance(token, str) and token.strip():
                return token.strip(), "bearer"
    return None, None


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = _extract_bearer_token(_get_header(scope, "authorization"))
        selected_subprotocol = None

        if not token:
            token, selected_subprotocol = _extract_token_from_subprotocols(scope)

        user = await _get_user_from_token(token) if token else None
        scope["user"] = user or AnonymousUser()
        if selected_subprotocol:
            scope["ws_auth_subprotocol"] = selected_subprotocol
        return await super().__call__(scope, receive, send)
