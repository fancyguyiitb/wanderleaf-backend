from rest_framework import serializers

from apps.messaging.models import Conversation, Message
from apps.messaging.services import is_booking_chat_active


class ChatUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(source="username", read_only=True)
    email = serializers.EmailField(read_only=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj) -> str | None:
        if not getattr(obj, "avatar", None):
            return None
        try:
            url = obj.avatar.url
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                return url
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None


class MessageSerializer(serializers.ModelSerializer):
    sender = ChatUserSummarySerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "body",
            "message_type",
            "attachment_url",
            "attachment_name",
            "attachment_mime",
            "attachment_bytes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(source="booking.id", read_only=True)
    booking_status = serializers.CharField(source="booking.status", read_only=True)
    booking_status_display = serializers.CharField(
        source="booking.get_status_display",
        read_only=True,
    )
    is_chat_available = serializers.SerializerMethodField()
    participants = ChatUserSummarySerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "booking_id",
            "booking_status",
            "booking_status_display",
            "is_chat_available",
            "participants",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_chat_available(self, obj) -> bool:
        if not obj.booking:
            return False
        return is_booking_chat_active(obj.booking)

