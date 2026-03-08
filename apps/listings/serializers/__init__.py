from django.db.models import Avg, Count
from rest_framework import serializers

from apps.bookings.services import BookingService
from apps.listings.models import Listing
from apps.reviews.models import Review
from apps.users.serializers import UserSerializer

# Fee constants exposed for frontend price calculation (must match BookingService)
SERVICE_FEE_PERCENT = 12
CLEANING_FEE_DEFAULT = 25


class HostSummarySerializer(serializers.Serializer):
    """Inline read-only representation of the host on a listing."""

    id = serializers.UUIDField(source="host.id", read_only=True)
    name = serializers.CharField(source="host.username", read_only=True)
    email = serializers.EmailField(source="host.email", read_only=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj) -> str | None:
        host = obj.host
        if not getattr(host, "avatar", None):
            return None
        try:
            url = host.avatar.url
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                return url
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None


class ListingListSerializer(serializers.ModelSerializer):
    """
    Compact serializer used for list views.
    Includes host summary but omits the full description.
    """

    host = HostSummarySerializer(source="*", read_only=True)
    rating = serializers.DecimalField(
        source="average_rating",
        max_digits=3,
        decimal_places=1,
        read_only=True,
    )

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "location",
            "category",
            "price_per_night",
            "bedrooms",
            "bathrooms",
            "max_guests",
            "amenities",
            "images",
            "latitude",
            "longitude",
            "is_active",
            "host",
            "rating",
            "review_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ListingDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer used for retrieve/detail views.
    Includes everything: full description, host details, booked dates for the
    calendar picker, and fee constants for frontend price calculation.
    """

    host = HostSummarySerializer(source="*", read_only=True)
    booked_dates = serializers.SerializerMethodField()
    service_fee_percent = serializers.SerializerMethodField()
    cleaning_fee = serializers.SerializerMethodField()
    rating = serializers.DecimalField(
        source="average_rating",
        max_digits=3,
        decimal_places=1,
        read_only=True,
    )
    review_count = serializers.IntegerField(read_only=True)
    rating_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "location",
            "category",
            "price_per_night",
            "bedrooms",
            "bathrooms",
            "max_guests",
            "amenities",
            "images",
            "latitude",
            "longitude",
            "is_active",
            "host",
            "booked_dates",
            "service_fee_percent",
            "cleaning_fee",
            "rating",
            "review_count",
            "rating_breakdown",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_booked_dates(self, obj) -> list[dict]:
        """
        Returns list of {check_in, check_out} for active bookings.
        Use these to disable dates in the calendar picker.
        """
        ranges = BookingService.get_booked_dates(str(obj.id))
        return [
            {
                "check_in": r["check_in"].isoformat(),
                "check_out": r["check_out"].isoformat(),
            }
            for r in ranges
        ]

    def get_service_fee_percent(self, obj) -> int:
        """Service fee percentage (12%) for frontend price calculation."""
        return SERVICE_FEE_PERCENT

    def get_cleaning_fee(self, obj) -> float:
        """Default cleaning fee for frontend price calculation."""
        return float(CLEANING_FEE_DEFAULT)

    def get_rating_breakdown(self, obj) -> list[dict]:
        """Count and percentage for each star rating (5 down to 1)."""
        counts = (
            Review.objects.filter(listing=obj)
            .values("rating")
            .annotate(count=Count("id"))
        )
        by_star = {r["rating"]: r["count"] for r in counts}
        total = sum(by_star.values())
        if total == 0:
            return [
                {"stars": s, "count": 0, "percentage": 0}
                for s in range(5, 0, -1)
            ]
        return [
            {
                "stars": s,
                "count": by_star.get(s, 0),
                "percentage": round(100 * by_star.get(s, 0) / total),
            }
            for s in range(5, 0, -1)
        ]


class ListingCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating listings.

    `host` is set automatically from the authenticated user
    and is not part of the request body.
    """

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "location",
            "category",
            "price_per_night",
            "bedrooms",
            "bathrooms",
            "max_guests",
            "amenities",
            "images",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_price_per_night(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_amenities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Amenities must be a list of strings.")
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each amenity must be a string.")
        return value

    def validate_images(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Images must be a list of URL strings.")
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each image must be a URL string.")
        return value
