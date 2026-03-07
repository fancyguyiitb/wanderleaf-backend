from django.db.models import F, OuterRef, Prefetch, Q, Subquery

from apps.messaging.models import Conversation, ConversationReadState, Message


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


def get_unread_count_for_user(user):
    """Total count of unread messages (from others) across all conversations for this user."""
    conv_q = Q(conversation__booking__guest=user) | Q(
        conversation__booking__listing__host=user
    )
    last_read_subq = Subquery(
        ConversationReadState.objects.filter(
            user=user,
            conversation=OuterRef("conversation"),
        ).values("last_read_at")[:1]
    )
    return (
        Message.objects.filter(conv_q)
        .exclude(sender=user)
        .annotate(last_read=last_read_subq)
        .filter(Q(last_read__isnull=True) | Q(created_at__gt=F("last_read")))
        .count()
    )


def get_inbox_conversations_with_unread(user):
    """
    Return conversations for inbox: user is participant, chat is active,
    ordered by last message timestamp desc. Each conversation is annotated
    with unread_count and last_message.
    """
    from apps.messaging.services import is_booking_chat_active

    convs = (
        get_user_conversations_queryset(user)
        .filter(booking__isnull=False)
        .select_related("booking", "booking__listing", "booking__guest", "booking__listing__host")
    )
    # Filter to active chat only
    result = []
    for conv in convs:
        if not conv.booking or not is_booking_chat_active(conv.booking):
            continue
        last_msg = conv.messages.order_by("-created_at").first()
        last_read = None
        try:
            rs = ConversationReadState.objects.get(user=user, conversation=conv)
            last_read = rs.last_read_at
        except ConversationReadState.DoesNotExist:
            pass
        unread = conv.messages.exclude(sender=user)
        if last_read:
            unread = unread.filter(created_at__gt=last_read)
        unread_count = unread.count()
        result.append(
            {
                "conversation": conv,
                "last_message": last_msg,
                "unread_count": unread_count,
            }
        )
    # Sort by last message created_at desc
    result.sort(
        key=lambda x: x["last_message"].created_at if x["last_message"] else x["conversation"].created_at,
        reverse=True,
    )
    return result

