from rest_framework import serializers
from .models import Album, Photo, AlbumTemplate, AlbumPage, PhotoEdit
from django.contrib.auth.models import User


# ============ БАЗОВЫЕ СЕРИАЛИЗАТОРЫ ============

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class AlbumTemplateSerializer(serializers.ModelSerializer):
    """Сериализатор шаблона альбома"""
    class Meta:
        model = AlbumTemplate
        fields = '__all__'


class AlbumPageSerializer(serializers.ModelSerializer):
    """Сериализатор страницы альбома"""
    class Meta:
        model = AlbumPage
        fields = '__all__'


class PhotoEditSerializer(serializers.ModelSerializer):
    """Сериализатор редактирования фото"""
    class Meta:
        model = PhotoEdit
        fields = '__all__'


# ============ ФОТО С ВАЛИДАЦИЕЙ ============

class PhotoSerializer(serializers.ModelSerializer):
    """Сериализатор фотографии с валидацией"""
    
    def validate_image(self, value):
        """ВАЛИДАЦИЯ: Максимальный размер файла (10 МБ)"""
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Максимальный размер файла: 10 МБ")
        return value
    
    def validate(self, data):
        """ВАЛИДАЦИЯ: Разрешенные форматы (JPEG, PNG, WEBP)"""
        if 'image' in self.initial_data:
            file_name = self.initial_data['image'].name
            allowed_formats = ['jpg', 'jpeg', 'png', 'webp']
            file_ext = file_name.split('.')[-1].lower()
            if file_ext not in allowed_formats:
                raise serializers.ValidationError({
                    'image': f"Разрешенные форматы: {', '.join(allowed_formats)}"
                })
        return data
    
    class Meta:
        model = Photo
        fields = ['id', 'album', 'image', 'title', 'description', 'uploaded_at', 'file_size']
        read_only_fields = ['id', 'uploaded_at', 'file_size']



# ============ АЛЬБОМ С ВАЛИДАЦИЕЙ ============

class AlbumSerializer(serializers.ModelSerializer):
    """Сериализатор альбома с полной валидацией"""
    user = UserSerializer(read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    pages = AlbumPageSerializer(many=True, read_only=True)
    layout_template = AlbumTemplateSerializer(read_only=True)
    photo_count = serializers.SerializerMethodField()
    
    def validate_title(self, value):
        """ВАЛИДАЦИЯ 2: Уникальное название альбома в рамках пользователя"""
        user = self.context['request'].user
        existing = Album.objects.filter(user=user, title=value)
        
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise serializers.ValidationError(
                "У вас уже есть альбом с таким названием"
            )
        return value
    
    def validate_layout_template(self, value):
        """ВАЛИДАЦИЯ 2: Проверка доступности шаблона"""
        if value and value.is_premium:
            user = self.context.get('request').user
            if user and not user.is_staff:
                raise serializers.ValidationError(
                    "Этот шаблон доступен только премиум пользователям"
                )
        return value
    
    def get_photo_count(self, obj):
        """Количество фотографий в альбоме"""
        return obj.photos.count() 
    
    class Meta:
        model = Album
        fields = [
            'id', 'user', 'title', 'description', 'cover_photo', 
            'is_public', 'created_at', 'updated_at', 'layout_template',
            'views_count', 'photos', 'pages', 'photo_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'views_count']
