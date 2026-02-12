from rest_framework import viewsets

from apps.messaging.models import Conversation, Message


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Placeholder ViewSet for conversations.
    """

    queryset = Conversation.objects.all()
    serializer_class = None  # to be defined


class MessageViewSet(viewsets.ModelViewSet):
    """
    Placeholder ViewSet for messages.
    """

    queryset = Message.objects.all()
    serializer_class = None  # to be defined

