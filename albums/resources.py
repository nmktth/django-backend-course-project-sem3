from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.db.models import Sum
from django.utils import timezone
from .models import Album, AlbumTemplate


class AlbumResource(resources.ModelResource):
    """Ресурс для экспорта альбомов в Excel с 5 кастомными полями"""
    
    user = fields.Field(attribute='user__username')
    layout_template = fields.Field(attribute='layout_template__name')
    
    # ========== 5 КАСТОМНЫХ ПОЛЕЙ ==========
    album_size_mb = fields.Field()
    completion_status = fields.Field()
    template_type_emoji = fields.Field()
    album_rating = fields.Field()
    recent_activity = fields.Field()
    
    class Meta:
        model = Album
        fields = (
            'id', 
            'title', 
            'user', 
            'description', 
            'is_public', 
            'created_at',
            'updated_at',
            'layout_template', 
            'views_count',
            'album_size_mb', 
            'completion_status', 
            'template_type_emoji', 
            'album_rating', 
            'recent_activity'
        )
        export_order = (
            'id', 
            'title', 
            'user', 
            'description', 
            'is_public',
            'created_at',
            'updated_at',
            'layout_template',
            'views_count',
            'album_size_mb',
            'completion_status', 
            'template_type_emoji',
            'album_rating', 
            'recent_activity'
        )
    
    # ========== DEHYDRATE МЕТОДЫ ==========
    
    def dehydrate_album_size_mb(self, obj):
        """
        КАСТОМНОЕ ПОЛЕ 1: Форматирование размера альбома
        Вычисляет общий размер всех фотографий в альбоме в МБ
        """
        total_size = obj.photos.aggregate(total=Sum('file_size'))['total'] or 0
        return f"{total_size / 1024 / 1024:.1f} МБ"
    
    def dehydrate_completion_status(self, obj):
        """
        КАСТОМНОЕ ПОЛЕ 2: Статус заполненности альбома
        Возвращает текстовый статус на основе количества фотографий
        """
        photo_count = obj.photos.count()
        if photo_count == 0:
            return "Пустой"
        elif photo_count < 10:
            return "Мало фото"
        elif photo_count < 50:
            return "Хорошо заполнен"
        else:
            return "Полностью заполнен"
    
    def dehydrate_template_type_emoji(self, obj):
        """
        КАСТОМНОЕ ПОЛЕ 3: Тип шаблона с эмодзи
        Возвращает шаблон с соответствующим эмодзи
        """
        if not obj.layout_template:
            return "📁 Нет шаблона"
        
        emoji_map = {
            'wedding': '💒',
            'travel': '✈️',
            'portrait': '👤',
            'family': '👪',
            'event': '🎉'
        }
        emoji = emoji_map.get(obj.layout_template.template_type, '📁')
        return f"{emoji} {obj.layout_template.name}"
    
    def dehydrate_album_rating(self, obj):
        """
        КАСТОМНОЕ ПОЛЕ 4: Рейтинг альбома по количеству просмотров
        Классифицирует альбом на основе популярности
        """
        views = obj.views_count or 0
        if views > 1000:
            return "⭐⭐⭐ Популярный"
        elif views > 100:
            return "⭐⭐ Средний"
        elif views > 10:
            return "⭐ Новый"
        else:
            return "⭐ Очень новый"
    
    def dehydrate_recent_activity(self, obj):
        """
        КАСТОМНОЕ ПОЛЕ 5: Временная активность альбома
        Показывает когда альбом был последний раз обновлен
        """
        days_ago = (timezone.now() - obj.updated_at).days
        if days_ago == 0:
            return "📍 Сегодня"
        elif days_ago == 1:
            return "📍 Вчера"
        elif days_ago <= 7:
            return f"📍 {days_ago} дней назад"
        elif days_ago <= 30:
            return f"📍 {days_ago // 7} недель назад"
        else:
            return "⏱️ Неактивный"
