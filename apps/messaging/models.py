from django.db import models

from apps.bookings.models import Booking
from apps.common.models import TimeStampedModel
from apps.users.models import User


class Conversation(TimeStampedModel):
    """
    One booking-scoped conversation between the guest and host.
    """

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="conversation",
        null=True,
        blank=True,
        help_text="Booking that owns this one-to-one conversation.",
    )
    participants = models.ManyToManyField(User, related_name="conversations")

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        if self.booking_id:
            return f"Conversation for booking {self.booking_id}"
        return f"Conversation {self.id}"


class Message(TimeStampedModel):
    """
    A text or media message inside a booking conversation.
    """

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages_sent")
    body = models.TextField(blank=True, default="")
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        help_text="Whether this is a text-only message or one that includes an attachment.",
    )
    attachment_url = models.URLField(blank=True, default="")
    attachment_name = models.CharField(max_length=255, blank=True, default="")
    attachment_mime = models.CharField(max_length=255, blank=True, default="")
    attachment_bytes = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"Message {self.id} in conversation {self.conversation_id}"

