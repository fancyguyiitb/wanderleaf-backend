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
        await self.accept()

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
        attachment_url = (payload.get("attachment_url") or "").strip()
        attachment_name = (payload.get("attachment_name") or "").strip()
        attachment_mime = (payload.get("attachment_mime") or "").strip()
        attachment_bytes = payload.get("attachment_bytes")
        requested_type = (payload.get("message_type") or "").strip()

        if not body and not attachment_url:
            raise ValueError("Message cannot be empty.")

        if attachment_url:
            inferred_type = (
                Message.MessageType.IMAGE
                if attachment_mime.startswith("image/")
                else Message.MessageType.FILE
            )
        else:
            inferred_type = Message.MessageType.TEXT

        message_type = requested_type or inferred_type
        if message_type not in Message.MessageType.values:
            raise ValueError("Invalid message type.")

        message = Message.objects.create(
            conversation=conversation,
            sender=self.scope["user"],
            body=body,
            message_type=message_type,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_mime=attachment_mime,
            attachment_bytes=attachment_bytes or None,
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


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        self.user_group_name = _notification_group_name(user.id)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

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
