from django.contrib.auth import get_user_model

from rest_framework import serializers


User = get_user_model()


def _normalize_phone_number(value: str) -> str:
    digits_only = "".join(ch for ch in value if ch.isdigit())
    if len(digits_only) < 8 or len(digits_only) > 15:
        raise serializers.ValidationError("Phone number must be between 8 and 15 digits.")
    return digits_only


def create_social_user(*, email: str, username: str, phone_number: str | None = None):
    normalized_phone = None
    if phone_number:
        normalized_phone = _normalize_phone_number(phone_number)
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise serializers.ValidationError({"phone_number": "Phone number is already in use."})

    user = User.objects.create_user(
        username=username,
        email=email.strip().lower(),
        phone_number=normalized_phone,
        password=None,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user."""

    avatar = serializers.SerializerMethodField()
    has_chat_key = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "avatar",
            "date_joined",
            "has_chat_key",
            "chat_key_algorithm",
            "chat_key_version",
            "chat_key_uploaded_at",
        ]
        read_only_fields = fields

    def get_avatar(self, obj) -> str | None:
        """
        Return an absolute URL for the user's avatar if available.
        Cloudinary storage returns absolute HTTPS URLs directly.
        """

        if not getattr(obj, "avatar", None):
            return None

        try:
            avatar_url = obj.avatar.url
            # Cloudinary returns absolute HTTPS URLs like:
            # https://res.cloudinary.com/{cloud_name}/image/upload/...
            if isinstance(avatar_url, str):
                # If it's already an absolute URL (Cloudinary), return it
                if avatar_url.startswith(("http://", "https://")):
                    return avatar_url
                # If it's a relative path (shouldn't happen with Cloudinary), build absolute
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(avatar_url)
                return avatar_url
            return str(avatar_url)
        except Exception:
            # If there's any error getting the URL, return None
            return None

    def get_has_chat_key(self, obj) -> bool:
        return obj.has_chat_key


class ChatKeyBackupSerializer(serializers.ModelSerializer):
    public_key = serializers.CharField(source="chat_public_key")
    key_algorithm = serializers.CharField(source="chat_key_algorithm")
    key_version = serializers.IntegerField(source="chat_key_version", min_value=1)
    encrypted_private_key = serializers.CharField(source="chat_private_key_backup")
    backup_iv = serializers.CharField(source="chat_private_key_backup_iv")
    backup_salt = serializers.CharField(source="chat_private_key_backup_salt")
    backup_kdf = serializers.CharField(source="chat_private_key_backup_kdf")
    backup_kdf_iterations = serializers.IntegerField(source="chat_private_key_backup_kdf_iterations", min_value=1)
    backup_cipher = serializers.CharField(source="chat_private_key_backup_cipher")
    backup_version = serializers.IntegerField(source="chat_private_key_backup_version", min_value=1)
    has_backup = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "has_backup",
            "public_key",
            "key_algorithm",
            "key_version",
            "encrypted_private_key",
            "backup_iv",
            "backup_salt",
            "backup_kdf",
            "backup_kdf_iterations",
            "backup_cipher",
            "backup_version",
            "chat_key_uploaded_at",
        ]
        read_only_fields = ["has_backup", "chat_key_uploaded_at"]

    def get_has_backup(self, obj) -> bool:
        return obj.has_chat_key

    def validate_public_key(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Public key is required.")
        return value

    def validate_key_algorithm(self, value: str) -> str:
        value = value.strip()
        if value != "RSA-OAEP-256":
            raise serializers.ValidationError("Unsupported chat key algorithm.")
        return value

    def validate_backup_kdf(self, value: str) -> str:
        value = value.strip()
        if value != "PBKDF2-SHA256":
            raise serializers.ValidationError("Unsupported chat key derivation function.")
        return value

    def validate_backup_cipher(self, value: str) -> str:
        value = value.strip()
        if value != "AES-GCM":
            raise serializers.ValidationError("Unsupported chat key backup cipher.")
        return value

    def validate(self, attrs):
        required_fields = [
            "chat_public_key",
            "chat_key_algorithm",
            "chat_key_version",
            "chat_private_key_backup",
            "chat_private_key_backup_iv",
            "chat_private_key_backup_salt",
            "chat_private_key_backup_kdf",
            "chat_private_key_backup_kdf_iterations",
            "chat_private_key_backup_cipher",
            "chat_private_key_backup_version",
        ]
        missing = [field for field in required_fields if not attrs.get(field)]
        if missing:
            raise serializers.ValidationError("Complete chat key backup metadata is required.")
        return attrs


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
        digits_only = _normalize_phone_number(value)
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



