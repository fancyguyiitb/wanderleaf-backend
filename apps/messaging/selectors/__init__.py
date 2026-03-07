from django.db.models import Prefetch, Q

from apps.messaging.models import Conversation, Message


def get_user_conversations_queryset(user):
    return (
        Conversation.objects.select_related("booking", "booking__listing", "booking__guest", "booking__listing__host")
        .prefetch_related(
            "participants",
            Prefetch(
                "messages",
                queryset=Message.objects.select_related("sender").order_by("created_at"),
            ),
        )
        .filter(
            Q(booking__guest=user) | Q(booking__listing__host=user)
        )
        .distinct()
    )


def get_conversation_for_user(conversation_id, user):
    return get_user_conversations_queryset(user).filter(id=conversation_id).first()

