from rest_framework import serializers

from apps.reviews.models import Review


class ReviewAuthorSerializer(serializers.Serializer):
    """Compact author info for review display."""

    id = serializers.UUIDField(source="author.id", read_only=True)
    name = serializers.CharField(source="author.username", read_only=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj) -> str | None:
        author = obj.author
        if not getattr(author, "avatar", None):
            return None
        try:
            url = author.avatar.url
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                return url
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None


class ReviewSerializer(serializers.ModelSerializer):
    """Read serializer for reviews."""

    author = ReviewAuthorSerializer(source="*", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "author", "rating", "comment", "created_at"]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    """Write serializer for creating a review."""

    booking_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_booking_id(self, value):
        from django.shortcuts import get_object_or_404

        from apps.bookings.models import Booking

        booking = get_object_or_404(
            Booking.objects.select_related("listing", "guest"),
            id=value,
        )
        user = self.context["request"].user

        if str(booking.guest_id) != str(user.id):
            raise serializers.ValidationError(
                "You can only review bookings where you were the guest."
            )

        if booking.status not in (
            Booking.Status.CONFIRMED,
            Booking.Status.COMPLETED,
        ):
            raise serializers.ValidationError(
                "You can only review confirmed or completed stays."
            )

        if hasattr(booking, "review") and booking.review:
            raise serializers.ValidationError(
                "You have already reviewed this stay."
            )

        self.context["booking"] = booking
        return value
