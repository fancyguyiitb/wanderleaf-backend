from rest_framework import serializers

from apps.listings.models import Listing
from apps.users.serializers import UserSerializer


class HostSummarySerializer(serializers.Serializer):
    """Inline read-only representation of the host on a listing."""

    id = serializers.IntegerField(source="host.id", read_only=True)
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ListingDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer used for retrieve/detail views.
    Includes everything: full description and host details.
    """

    host = HostSummarySerializer(source="*", read_only=True)

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


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
