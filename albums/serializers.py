from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Album, Photo, Collage, BugReport


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password_confirm")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        return attrs

    def create(self, validated_data):
        """Create user instance."""
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user

    def update(self, instance, validated_data):
        """Stub to satisfy abstract method."""
        return super().update(instance, validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра и обновления профиля."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "username", "date_joined")


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def create(self, validated_data):
        """Stub to satisfy abstract method."""
        return super().create(validated_data)  # pylint: disable=no-member

    def update(self, instance, validated_data):
        """Stub to satisfy abstract method."""
        return super().update(instance, validated_data)  # pylint: disable=no-member

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Новые пароли не совпадают."}
            )
        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = "__all__"
        read_only_fields = ("album",)

    def validate_image(self, value):
        """
        Проверка загружаемого изображения (Section 3.1).
        Business Logic Validation 3: Size and Format checks.
        """
        limit_mb = 10
        if value.size > limit_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Размер файла не может превышать {limit_mb} MB.")

        if not value.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            raise serializers.ValidationError("Разрешены только форматы JPEG, PNG, WEBP.")

        return value


class BugReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugReport
        fields = "__all__"
        read_only_fields = (
            "user",
            "created_at",
        )


class CollageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collage
        fields = "__all__"


class AlbumSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    collages = CollageSerializer(many=True, read_only=True)

    class Meta:
        model = Album
        fields = "__all__"
        read_only_fields = ("user", "created_at", "updated_at")

    def validate_title(self, value):
        """Business Logic Validation: Ban words + Unique title."""
        forbidden_words = ["admin", "root", "superuser", "banned"]
        if any(word in value.lower() for word in forbidden_words):
            raise serializers.ValidationError("Название альбома содержит запрещенные слова.")

        # Unique check
        user = self.context["request"].user
        if Album.objects.filter(user=user, title=value).exists() and not self.instance:
            raise serializers.ValidationError("У вас уже есть альбом с таким названием.")

        return value

    def validate(self, data):
        """Business Logic Validation: Description required for public albums + Limit check."""
        # 1. Description check
        is_public = data.get("is_public", False)
        description = data.get("description", "")

        if is_public and not description:
            raise serializers.ValidationError(
                {"description": "Публичные альбомы должны иметь описание."}
            )

        # 2. Limit check (moved from validate, usually good to have in validate or view)
        user = self.context["request"].user
        if not self.instance:
            if Album.objects.filter(user=user).count() >= 20:
                raise serializers.ValidationError("Вы достигли лимита в 20 альбомов.")

        return data
