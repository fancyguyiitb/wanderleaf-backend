from django.contrib.auth import get_user_model

from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone_number", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Simple registration serializer.

    For now we register by username + email + phone_number + password.
    """

    password = serializers.CharField(write_only=True, min_length=8)

    phone_number = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone_number", "password"]
        read_only_fields = ["id"]

    def validate_phone_number(self, value: str) -> str:
        digits_only = "".join(ch for ch in value if ch.isdigit())
        if len(digits_only) < 8 or len(digits_only) > 15:
            raise serializers.ValidationError("Phone number must be between 8 and 15 digits.")
        # Enforce uniqueness at the serializer level so we return 400 instead of 500.
        if User.objects.filter(phone_number=digits_only).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return digits_only

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            username=validated_data["username"],  # full name
            email=validated_data.get("email", ""),
            phone_number=validated_data["phone_number"],
            password=password,
        )
        return user



