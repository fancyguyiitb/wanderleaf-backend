import uuid

import cloudinary.uploader
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.messaging.selectors import (
    get_conversation_for_user,
    get_inbox_conversations_with_unread,
    get_unread_count_for_user,
)
from apps.messaging.serializers import ChatUserSummarySerializer, ConversationSerializer
from apps.messaging.services import (
    can_access_booking_chat,
    get_or_create_conversation_for_booking,
    is_booking_chat_active,
    mark_conversation_as_read,
)


def _get_booking_for_user(user, booking_id: str) -> Booking:
    try:
        uuid.UUID(str(booking_id))
    except ValueError:
        from rest_framework.exceptions import NotFound
        raise NotFound(detail="Booking not found.")

    return get_object_or_404(
        Booking.objects.select_related("guest", "listing", "listing__host"),
        Q(guest=user) | Q(listing__host=user),
        id=booking_id,
    )


class BookingConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, booking_id: str):
        booking = _get_booking_for_user(request.user, booking_id)

        if not can_access_booking_chat(request.user, booking):
            return Response(
                {"detail": "You do not have access to this booking chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_booking_chat_active(booking):
            return Response(
                {"detail": "Chat is unavailable for this booking."},
                status=status.HTTP_403_FORBIDDEN,
            )

        conversation = get_or_create_conversation_for_booking(booking)
        conversation = (
            conversation.__class__.objects.select_related(
                "booking", "booking__guest", "booking__listing", "booking__listing__host"
            )
            .prefetch_related("participants", "messages__sender")
            .get(id=conversation.id)
        )
        mark_conversation_as_read(request.user, conversation)
        serializer = ConversationSerializer(conversation, context={"request": request})
        return Response(serializer.data)


class ConversationAttachmentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, conversation_id: str):
        conversation = get_conversation_for_user(conversation_id, request.user)
        if not conversation or not conversation.booking:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not is_booking_chat_active(conversation.booking):
            return Response(
                {"detail": "Chat is unavailable for this booking."},
                status=status.HTTP_403_FORBIDDEN,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "No file uploaded. Send the attachment using the 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_types = {
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
            "image/gif",
            "video/mp4",
            "video/webm",
            "video/quicktime",
            "application/pdf",
        }
        max_size = 25 * 1024 * 1024

        if file_obj.content_type not in allowed_types:
            return Response(
                {"detail": f"Unsupported attachment type '{file_obj.content_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file_obj.size > max_size:
            return Response(
                {"detail": "Attachment exceeds the 25 MB limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            upload_result = cloudinary.uploader.upload(
                file_obj,
                folder="wanderleaf/messages",
                resource_type="auto",
            )
        except Exception as exc:
            return Response(
                {"detail": f"Attachment upload failed: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = file_obj.content_type or ""
        message_type = "image" if content_type.startswith("image/") else "file"

        return Response(
            {
                "attachment_url": upload_result["secure_url"],
                "attachment_name": file_obj.name,
                "attachment_mime": content_type,
                "attachment_bytes": file_obj.size,
                "message_type": message_type,
            },
            status=status.HTTP_201_CREATED,
        )


class MarkConversationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id: str):
        conversation = get_conversation_for_user(conversation_id, request.user)
        if not conversation or not conversation.booking:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not is_booking_chat_active(conversation.booking):
            return Response(
                {"detail": "Chat is unavailable for this booking."},
                status=status.HTTP_403_FORBIDDEN,
            )
        mark_conversation_as_read(request.user, conversation)
        return Response({"detail": "ok"})


class InboxListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = get_inbox_conversations_with_unread(request.user)
        data = []
        for item in items:
            conv = item["conversation"]
            last_msg = item["last_message"]
            other = next(
                (p for p in conv.participants.all() if p.id != request.user.id),
                None,
            )
            if not other:
                continue
            booking = conv.booking
            preview = ""
            last_at = None
            if last_msg:
                last_at = last_msg.created_at
                if last_msg.is_encrypted:
                    preview = "Encrypted message"
                elif last_msg.body:
                    preview = (last_msg.body or "")[:200]
                elif last_msg.message_type == "image":
                    preview = "Image"
                else:
                    preview = last_msg.attachment_name or "File"
            user_serializer = ChatUserSummarySerializer(
                other, context={"request": request}
            )
            data.append(
                {
                    "id": str(conv.id),
                    "booking_id": str(booking.id),
                    "booking_title": booking.listing.title,
                    "is_chat_available": is_booking_chat_active(booking),
                    "other_participant": user_serializer.data,
                    "last_message": preview,
                    "last_message_at": last_at,
                    "unread_count": item["unread_count"],
                }
            )
        return Response(data)


class UnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total = get_unread_count_for_user(request.user)
        return Response({"total": total})
