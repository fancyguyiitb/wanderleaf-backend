from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from apps.messaging.models import Message
from apps.messaging.selectors import get_conversation_for_user
from apps.messaging.serializers import MessageSerializer
from apps.messaging.services import is_booking_chat_active


def _notification_group_name(user_id) -> str:
    return f"user_{user_id}"


class BookingChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"conversation_{self.conversation_id}"

        can_connect = await self._can_connect()
        if not can_connect:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept(self.scope.get("ws_auth_subprotocol"))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        if action != "message.send":
            await self.send_json(
                {"type": "error", "detail": f"Unsupported action '{action}'."}
            )
            return

        try:
            message_data = await self._create_message(content.get("payload") or {})
        except ValueError as exc:
            await self.send_json({"type": "error", "detail": str(exc)})
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.message_created", "message": message_data["message"]},
        )
        for recipient_id in message_data["recipient_ids"]:
            await self.channel_layer.group_send(
                _notification_group_name(recipient_id),
                {
                    "type": "notification.message_created",
                    "notification": message_data["notification"],
                },
            )

    async def chat_message_created(self, event):
        await self.send_json(
            {"type": "message.created", "message": event["message"]}
        )

    @database_sync_to_async
    def _can_connect(self) -> bool:
        conversation = get_conversation_for_user(self.conversation_id, self.scope["user"])
        return bool(
            conversation
            and conversation.booking
            and is_booking_chat_active(conversation.booking)
        )

    @database_sync_to_async
    def _create_message(self, payload: dict):
        conversation = get_conversation_for_user(self.conversation_id, self.scope["user"])
        if not conversation or not conversation.booking:
            raise ValueError("Conversation not found.")

        if not is_booking_chat_active(conversation.booking):
            raise ValueError("Chat is unavailable for this booking.")

        body = (payload.get("body") or "").strip()
        encrypted_body = self._normalize_encrypted_body(payload.get("encrypted_body"))
        attachment_url = (payload.get("attachment_url") or "").strip()
        attachment_name = (payload.get("attachment_name") or "").strip()
        attachment_mime = (payload.get("attachment_mime") or "").strip()
        attachment_bytes = payload.get("attachment_bytes")
        requested_type = (payload.get("message_type") or "").strip()

        if encrypted_body and body:
            raise ValueError("Encrypted messages must not include plaintext body content.")
        if encrypted_body and attachment_url:
            raise ValueError("Encrypted attachment metadata must not be sent in plaintext.")

        if not body and not encrypted_body and not attachment_url:
            raise ValueError("Message cannot be empty.")

        if body and not encrypted_body:
            raise ValueError("Text messages must be end-to-end encrypted.")

        if attachment_url:
            inferred_type = (
                Message.MessageType.IMAGE
                if attachment_mime.startswith("image/")
                else Message.MessageType.FILE
            )
        elif encrypted_body and requested_type in (Message.MessageType.IMAGE, Message.MessageType.FILE):
            inferred_type = requested_type
        else:
            inferred_type = Message.MessageType.TEXT

        message_type = requested_type or inferred_type
        if message_type not in Message.MessageType.values:
            raise ValueError("Invalid message type.")

        message = Message.objects.create(
            conversation=conversation,
            sender=self.scope["user"],
            body=body if not encrypted_body else "",
            encrypted_body=encrypted_body,
            message_type=message_type,
            attachment_url=attachment_url if not encrypted_body else "",
            attachment_name=attachment_name if not encrypted_body else "",
            attachment_mime=attachment_mime if not encrypted_body else "",
            attachment_bytes=(attachment_bytes or None) if not encrypted_body else None,
        )
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

        serialized_message = MessageSerializer(message).data
        recipient_ids = [
            str(participant.id)
            for participant in conversation.participants.exclude(id=self.scope["user"].id)
        ]
        notification = {
            "booking_id": str(conversation.booking_id),
            "conversation_id": str(conversation.id),
            "booking_title": conversation.booking.listing.title,
            "message": serialized_message,
        }

        return {
            "message": serialized_message,
            "recipient_ids": recipient_ids,
            "notification": notification,
        }

    def _normalize_encrypted_body(self, value):
        if value in (None, ""):
            return None
        if not isinstance(value, dict):
            raise ValueError("Encrypted message payload is invalid.")

        required_fields = [
            "ciphertext",
            "iv",
            "wrapped_keys",
            "algorithm",
            "key_algorithm",
            "version",
            "sender_key_version",
        ]
        if any(field not in value for field in required_fields):
            raise ValueError("Encrypted message payload is incomplete.")

        if value.get("algorithm") != "AES-GCM":
            raise ValueError("Encrypted message payload uses an unsupported cipher.")
        if value.get("key_algorithm") != "RSA-OAEP-256":
            raise ValueError("Encrypted message payload uses an unsupported key algorithm.")

        wrapped_keys = value.get("wrapped_keys")
        if not isinstance(wrapped_keys, dict) or not wrapped_keys:
            raise ValueError("Encrypted message payload is missing wrapped keys.")

        for recipient_id, wrapped_key_data in wrapped_keys.items():
            if not recipient_id or not isinstance(wrapped_key_data, dict):
                raise ValueError("Encrypted message payload contains invalid wrapped keys.")
            if not wrapped_key_data.get("wrapped_key"):
                raise ValueError("Encrypted message payload contains an empty wrapped key.")
            if not wrapped_key_data.get("key_version"):
                raise ValueError("Encrypted message payload contains an invalid key version.")

        return {
            "ciphertext": value["ciphertext"],
            "iv": value["iv"],
            "wrapped_keys": wrapped_keys,
            "algorithm": value["algorithm"],
            "key_algorithm": value["key_algorithm"],
            "version": value["version"],
            "sender_key_version": value["sender_key_version"],
        }


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        self.user_group_name = _notification_group_name(user.id)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept(self.scope.get("ws_auth_subprotocol"))

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        await self.send_json({"type": "error", "detail": "Notifications socket is read-only."})

    async def notification_message_created(self, event):
        await self.send_json(
            {
                "type": "notification.message_created",
                "notification": event["notification"],
            }
        )
