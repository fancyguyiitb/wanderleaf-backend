from datetime import date

from rest_framework import serializers

from apps.bookings.models import Booking
from apps.listings.models import Listing


class ListingSummarySerializer(serializers.Serializer):
    """Compact listing info for booking responses."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    location = serializers.CharField(read_only=True)
    images = serializers.JSONField(read_only=True)
    price_per_night = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        fields = ["id", "title", "location", "images", "price_per_night"]


class GuestSummarySerializer(serializers.Serializer):
    """Compact guest info for booking responses."""

    id = serializers.UUIDField(source="guest.id", read_only=True)
    name = serializers.CharField(source="guest.username", read_only=True)
    email = serializers.EmailField(source="guest.email", read_only=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj) -> str | None:
        guest = obj.guest
        if not getattr(guest, "avatar", None):
            return None
        try:
            url = guest.avatar.url
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                return url
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None


class HostSummarySerializer(serializers.Serializer):
    """Compact host info for booking responses."""

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


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for listing bookings (compact view)."""

    listing = ListingSummarySerializer(read_only=True)
    guest = GuestSummarySerializer(source="*", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "listing",
            "guest",
            "check_in",
            "check_out",
            "num_guests",
            "num_nights",
            "total_price",
            "status",
            "status_display",
            "created_at",
        ]
        read_only_fields = fields


class BookingDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed booking view."""

    listing = ListingSummarySerializer(read_only=True)
    guest = GuestSummarySerializer(source="*", read_only=True)
    host = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    payment_retry_disallowed = serializers.BooleanField(read_only=True)
    payment_deadline_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "listing",
            "guest",
            "host",
            "check_in",
            "check_out",
            "num_guests",
            "price_per_night",
            "num_nights",
            "subtotal",
            "service_fee",
            "cleaning_fee",
            "total_price",
            "status",
            "status_display",
            "can_be_cancelled",
            "payment_retry_disallowed",
            "payment_deadline_seconds",
            "special_requests",
            "cancellation_reason",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]

    def get_payment_deadline_seconds(self, obj) -> int:
        from apps.bookings.services import BookingService
        return BookingService.get_seconds_until_payment_expiry(obj)
        read_only_fields = fields

    def get_host(self, obj) -> dict:
        host = obj.listing.host
        return HostSummarySerializer(host, context=self.context).data


class BookingCreateSerializer(serializers.Serializer):
    """Serializer for creating a new booking."""

    listing_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    num_guests = serializers.IntegerField(min_value=1)
    special_requests = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_listing_id(self, value):
        try:
            listing = Listing.objects.get(id=value, is_active=True)
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Listing not found or is not available.")
        self.context["listing"] = listing
        return value

    def validate_check_in(self, value):
        if value < date.today():
            raise serializers.ValidationError("Check-in date cannot be in the past.")
        return value

    def validate_check_out(self, value):
        if value < date.today():
            raise serializers.ValidationError("Check-out date cannot be in the past.")
        return value

    def validate(self, attrs):
        check_in = attrs.get("check_in")
        check_out = attrs.get("check_out")
        num_guests = attrs.get("num_guests")

        if check_out <= check_in:
            raise serializers.ValidationError({
                "check_out": "Check-out date must be after check-in date."
            })

        listing = self.context.get("listing")
        if listing and num_guests > listing.max_guests:
            raise serializers.ValidationError({
                "num_guests": f"This listing allows a maximum of {listing.max_guests} guests."
            })

        user = self.context.get("request").user
        if listing and str(listing.host_id) == str(user.id):
            raise serializers.ValidationError({
                "listing_id": "You cannot book your own listing."
            })

        return attrs


class BookingCancelSerializer(serializers.Serializer):
    """Serializer for cancelling a booking."""

    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CheckAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking listing availability."""

    listing_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()

    def validate_listing_id(self, value):
        try:
            Listing.objects.get(id=value, is_active=True)
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Listing not found or is not available.")
        return value

    def validate(self, attrs):
        check_in = attrs.get("check_in")
        check_out = attrs.get("check_out")

        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError({
                "check_out": "Check-out date must be after check-in date."
            })
        return attrs


class PriceCalculationSerializer(serializers.Serializer):
    """Serializer for price calculation request."""

    listing_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    num_guests = serializers.IntegerField(min_value=1)
