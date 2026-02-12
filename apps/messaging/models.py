from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class Conversation(TimeStampedModel):
    """
    Skeleton conversation model.
    """

    participants = models.ManyToManyField(User, related_name="conversations")


class Message(TimeStampedModel):
    """
    Skeleton message model.
    """

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages_sent")
    body = models.TextField()

