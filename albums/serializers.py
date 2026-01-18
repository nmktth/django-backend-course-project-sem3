from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Album, Photo, AlbumTemplate, AlbumPage, PhotoEdit

User = get_user_model()


class PhotoEditSerializer(serializers.ModelSerializer):
    """Сериализатор редактирования фото"""
    
    class Meta:
        model = PhotoEdit
        fields = [
            'id', 'photo', 'filters_applied', 'crop_data',
            'brightness', 'contrast', 'saturation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Валидация значений фильтров"""
        for field in ['brightness', 'contrast', 'saturation']:
            value = data.get(field, 0)
            if not (-100 <= value <= 100):
                raise serializers.ValidationError(
                    f'{field} должен быть от -100 до 100'
                )
        return data


class PhotoSerializer(serializers.ModelSerializer):
    """Сериализатор фотографии"""
    edits = PhotoEditSerializer(many=True, read_only=True)
    edits_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Photo
        fields = [
            'id', 'album', 'image', 'title', 'description',
            'uploaded_at', 'file_size', 'dimensions', 'order_index',
            'edits', 'edits_count'
        ]
        read_only_fields = ['id', 'uploaded_at', 'file_size']
    
    def get_edits_count(self, obj):
        return obj.edits.count()
    
    def validate(self, data):
        """Валидация: максимум 100 фото в альбоме"""
        album = data.get('album', self.instance.album if self.instance else None)
        if album and album.photos.exclude(pk=self.instance.pk if self.instance else None).count() >= 100:
            raise serializers.ValidationError('Максимум 100 фотографий в альбоме')
        return data


class AlbumPageSerializer(serializers.ModelSerializer):
    """Сериализатор страницы альбома"""
    
    class Meta:
        model = AlbumPage
        fields = ['id', 'album', 'page_number', 'layout', 'background_color', 'title']
        read_only_fields = ['id']


class AlbumTemplateSerializer(serializers.ModelSerializer):
    """Сериализатор шаблона альбома"""
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    
    class Meta:
        model = AlbumTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'template_type_display',
            'thumbnail', 'css_styles', 'is_premium',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlbumListSerializer(serializers.ModelSerializer):
    """Сериализатор списка альбомов (для пагинации)"""
    photos_count = serializers.SerializerMethodField()
    template_name = serializers.CharField(source='layout_template.name', read_only=True)
    album_size_mb = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Album
        fields = [
            'id', 'title', 'description', 'is_public',
            'created_at', 'updated_at',
            'photos_count', 'template_name', 'album_size_mb', 'user_username'
        ]
    
    def get_photos_count(self, obj):
        return obj.photos.count()
    
    def get_album_size_mb(self, obj):
        from django.db.models import Sum
        total_size = obj.photos.aggregate(total=Sum('file_size'))['total'] or 0
        return round(total_size / 1024 / 1024, 2)


class AlbumDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор альбома"""
    photos = PhotoSerializer(many=True, read_only=True)
    pages = AlbumPageSerializer(many=True, read_only=True)
    template_details = AlbumTemplateSerializer(source='layout_template', read_only=True)
    photos_count = serializers.SerializerMethodField()
    album_size_mb = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_is_premium = serializers.BooleanField(source='user.is_premium', read_only=True)
    
    class Meta:
        model = Album
        fields = [
            'id', 'user', 'user_username', 'user_is_premium', 'title', 'description',
            'cover_photo', 'is_public', 'created_at', 'updated_at',
            'layout_template', 'template_details', 
            'photos', 'pages', 'photos_count', 'album_size_mb'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Комплексная валидация"""
        user = data.get('user', self.instance.user if self.instance else None)
        
        # Проверка максимума альбомов
        if user and user.albums.exclude(pk=self.instance.pk if self.instance else None).count() >= 20:
            raise serializers.ValidationError('Максимум 20 альбомов на пользователя')
        
        # Проверка премиум шаблона
        layout_template = data.get('layout_template', self.instance.layout_template if self.instance else None)
        if layout_template and layout_template.is_premium:
            request = self.context.get('request')
            if request and not request.user.is_premium:
                raise serializers.ValidationError(
                    f'Шаблон "{layout_template.name}" доступен только для премиум пользователей'
                )
        
        # Проверка уникальности названия
        title = data.get('title')
        if title and user:
            duplicate = Album.objects.filter(user=user, title=title).exclude(
                pk=self.instance.pk if self.instance else None
            )
            if duplicate.exists():
                raise serializers.ValidationError('У вас уже есть альбом с таким названием')
        
        return data
    
    def get_photos_count(self, obj):
        return obj.photos.count()
    
    def get_album_size_mb(self, obj):
        from django.db.models import Sum
        total_size = obj.photos.aggregate(total=Sum('file_size'))['total'] or 0
        return round(total_size / 1024 / 1024, 2)


class AlbumCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания альбома"""
    
    class Meta:
        model = Album
        fields = [
            'id', 'title', 'description', 'is_public',
            'layout_template', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Валидация при создании"""
        user = self.context['request'].user
        
        # Проверка максимума альбомов
        if user.albums.count() >= 20:
            raise serializers.ValidationError('Максимум 20 альбомов на пользователя')
        
        # Проверка премиум шаблона
        layout_template = data.get('layout_template')
        if layout_template and layout_template.is_premium and not user.is_premium:
            raise serializers.ValidationError(
                f'Шаблон "{layout_template.name}" доступен только для премиум пользователей'
            )
        
        # Проверка уникальности названия
        title = data.get('title')
        if user.albums.filter(title=title).exists():
            raise serializers.ValidationError('У вас уже есть альбом с таким названием')
        
        return data
    
    def create(self, validated_data):
        """Создание альбома с текущим пользователем"""
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)
