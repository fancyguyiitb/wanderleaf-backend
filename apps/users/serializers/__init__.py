from django.contrib.auth import get_user_model

from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user."""

    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone_number", "avatar", "date_joined"]
        read_only_fields = ["id", "date_joined", "avatar"]

    def get_avatar(self, obj) -> str | None:
        """
        Return an absolute URL for the user's avatar if available.
        """

        if not getattr(obj, "avatar", None):
            return None

        request = self.context.get("request")
        if request is None:
            # Fallback to relative URL
            return obj.avatar.url

        return request.build_absolute_uri(obj.avatar.url)


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

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        # allow duplicate names, so no uniqueness check here
        return value

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


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Used for PATCH/PUT on the current user.

    All fields are optional; only provided fields are validated and updated.
    """

    class Meta:
        model = User
        fields = ["username", "email", "phone_number"]
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "phone_number": {"required": False},
        }

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        return value

    def validate_email(self, value: str) -> str:
        # enforce uniqueness excluding current user
        user_id = self.instance.id if self.instance else None
        qs = User.objects.filter(email__iexact=value)
        if user_id is not None:
            qs = qs.exclude(id=user_id)
        if qs.exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def validate_phone_number(self, value: str) -> str:
        digits_only = "".join(ch for ch in value if ch.isdigit())
        if len(digits_only) < 8 or len(digits_only) > 15:
            raise serializers.ValidationError("Phone number must be between 8 and 15 digits.")
        user_id = self.instance.id if self.instance else None
        qs = User.objects.filter(phone_number=digits_only)
        if user_id is not None:
            qs = qs.exclude(id=user_id)
        if qs.exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return digits_only



