from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import filters, FilterSet
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import serializers
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from .models import Album, Photo, AlbumTemplate, AlbumPage, PhotoEdit
from .serializers import (
    AlbumSerializer, PhotoSerializer, AlbumTemplateSerializer,
    AlbumPageSerializer, PhotoEditSerializer
)
from .resources import AlbumResource


# ============ FILTERSETS ============

class PhotoFilterSet(FilterSet):
    """Фильтры для фотографий"""
    file_size_min = filters.NumberFilter(field_name='file_size', lookup_expr='gte')
    file_size_max = filters.NumberFilter(field_name='file_size', lookup_expr='lte')
    uploaded_date = filters.CharFilter(field_name='uploaded_at__date', lookup_expr='icontains')
    
    class Meta:
        model = Photo
        fields = ['album', 'uploaded_at']


class AlbumFilterSet(FilterSet):
    """Фильтры для альбомов"""
    template = filters.CharFilter(field_name='layout_template__template_type', lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Album
        fields = ['is_public', 'layout_template']


# ============ VIEWSETS ============

class AlbumViewSet(ModelViewSet):
    serializer_class = AlbumSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AlbumFilterSet
    search_fields = ['title', 'description', 'user__username']
    ordering_fields = ['created_at', 'updated_at', 'views_count']
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Album.objects.filter(
                Q(user=self.request.user) | Q(is_public=True)
            ).prefetch_related('photos', 'pages')
        return Album.objects.filter(is_public=True).prefetch_related('photos', 'pages')
    
    def perform_create(self, serializer):
        """Валидация создания альбома"""
        user_albums_count = Album.objects.filter(user=self.request.user).count()
        if user_albums_count >= 20:
            raise serializers.ValidationError(
                {'error': 'Максимум 20 альбомов на пользователя'}
            )
        
        template_id = self.request.data.get('layout_template')
        if template_id:
            template = get_object_or_404(AlbumTemplate, id=template_id)
            if template.is_premium and not self.request.user.is_staff:
                raise serializers.ValidationError(
                    {'error': 'Этот шаблон только для премиум пользователей'}
                )
        
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """Опубликовать альбом"""
        album = self.get_object()
        
        if album.user != request.user:
            return Response(
                {'error': 'Только владелец может опубликовать альбом'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if album.photos.count() < 3:
            return Response(
                {'error': 'Альбом должен содержать минимум 3 фотографии'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        album.is_public = True
        album.save()
        return Response({'status': 'Album published', 'data': AlbumSerializer(album).data})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def apply_template(self, request, pk=None):
        """Применить шаблон к альбому"""
        album = self.get_object()
        
        if album.user != request.user:
            return Response(
                {'error': 'Только владелец может изменять альбом'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        template_id = request.data.get('template_id')
        template = get_object_or_404(AlbumTemplate, id=template_id)
        
        if template.is_premium and not request.user.is_staff:
            return Response(
                {'error': 'Этот шаблон доступен только премиум пользователям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        album.layout_template = template
        album.save()
        return Response(AlbumSerializer(album).data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def user_albums_stats(self, request):
        """МЕТОД 1: Статистика альбомов пользователя"""
        user_albums = Album.objects.filter(user=request.user)
        total_size = Photo.objects.filter(
            album__user=request.user
        ).aggregate(total=Sum('file_size'))['total'] or 0
        
        popular_templates = user_albums.values(
            'layout_template__name'
        ).annotate(count=Count('id')).order_by('-count')[:5]
        
        stats = {
            'total_albums': user_albums.count(),
            'total_photos': Photo.objects.filter(album__user=request.user).count(),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'public_albums': user_albums.filter(is_public=True).count(),
            'private_albums': user_albums.filter(is_public=False).count(),
            'popular_templates': list(popular_templates),
        }
        return Response(stats)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def duplicate_album(self, request, pk=None):
        """МЕТОД 3: Создать копию альбома"""
        original = self.get_object()
        
        if original.user != request.user:
            return Response(
                {'error': 'Only owner can duplicate'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_albums_count = Album.objects.filter(user=request.user).count()
        if user_albums_count >= 20:
            return Response(
                {'error': 'Достигнут максимум альбомов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_album = Album.objects.create(
            user=original.user,
            title=f"{original.title} (копия)",
            description=original.description,
            layout_template=original.layout_template,
        )
        
        for photo in original.photos.all():
            Photo.objects.create(
                album=new_album,
                image=photo.image,
                title=photo.title,
                description=photo.description,
                file_size=photo.file_size,
                dimensions=photo.dimensions,
                order_index=photo.order_index,
            )
        
        return Response(
            AlbumSerializer(new_album).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_share_link(self, request, pk=None):
        """МЕТОД 4: Сгенерировать ссылку для общего доступа"""
        album = self.get_object()
        
        if album.user != request.user:
            return Response(
                {'error': 'Only owner can generate link'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        share_link = f"/api/albums/{album.id}/?share=true"
        return Response({
            'share_link': share_link,
            'album_id': album.id,
            'album_title': album.title
        })
    
    @action(detail=False, methods=['get'])
    def albums_for_editing(self, request):
        """Q ЗАПРОС 1: Альбомы для редактирования
        Альбомы с неотсортированными фото ИЛИ требующие обложки, НЕ опубликованные"""
        albums = Album.objects.filter(
            Q(photos__order_index__isnull=True) | Q(cover_photo__isnull=True),
            is_public=False
        ).distinct()
        return Response(AlbumSerializer(albums, many=True).data)
    
    @action(detail=False, methods=['get'])
    def template_suggestions(self, request):
        """Q ЗАПРОС 2: Подбор шаблонов
        Шаблоны для вертикальных или горизонтальных фото, НЕ премиум для бесплатных"""
        templates = AlbumTemplate.objects.filter(
            Q(template_type__in=['portrait', 'travel']),
            is_premium=False
        )
        return Response(AlbumTemplateSerializer(templates, many=True).data)
    
    @action(detail=False, methods=['get'])
    def popular_albums(self, request):
        """Q ЗАПРОС 4: Аналитика популярности
        Публичные альбомы с многими просмотрами, НЕ старые архивные"""
        recent_date = timezone.now() - timedelta(days=90)
        albums = Album.objects.filter(
            Q(views_count__gt=100),
            is_public=True,
            updated_at__gte=recent_date
        ).order_by('-views_count')[:10]
        return Response(AlbumSerializer(albums, many=True).data)
    
    @action(detail=False, methods=['get'])
    def storage_optimization(self, request):
        """Q ЗАПРОС 5: Оптимизация хранения
        Альбомы с большими файлами ИЛИ дубликатами, НЕ системные служебные"""
        albums = Album.objects.annotate(
            total_size=Sum('photos__file_size'),
            photo_count=Count('photos')
        ).filter(
            Q(total_size__gt=500*1024*1024) | Q(photo_count__gt=50),
            user__is_staff=False  # НЕ администраторы
        ).exclude(
            user__username__startswith='admin'
        )
        
        return Response([{
            'id': a.id,
            'title': a.title,
            'total_size_mb': round((a.total_size or 0) / 1024 / 1024, 2),
            'photo_count': a.photo_count,
            'user': a.user.username
        } for a in albums])
    
    @action(detail=False, methods=['get'])
    def search_public(self, request):
        """Поиск по публичным альбомам"""
        query = request.query_params.get('q', '')
        albums = Album.objects.filter(
            is_public=True
        ).filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(user__username__icontains=query)
        ).order_by('-views_count')
        return Response(AlbumSerializer(albums, many=True).data)
    
    @action(detail=False, methods=['get'])
    def public_albums_by_user(self, request):
        """ФИЛЬТР 5: Публичные альбомы по пользователю и дате
        GET /api/albums/public_albums_by_user/?user=username&created_after=2024-01-01"""
        username = request.query_params.get('user')
        created_after = request.query_params.get('created_after')
        
        queryset = Album.objects.filter(is_public=True)
        
        if username:
            queryset = queryset.filter(user__username=username)
        
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)
        
        return Response(AlbumSerializer(queryset, many=True).data)
    
    @action(detail=False, methods=['get'])
    def search_all(self, request):
        """Полный поиск по альбомам, фото, шаблонам"""
        query = request.query_params.get('q', '')
        
        albums = Album.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(user__username__icontains=query)
        ).filter(Q(user=request.user) | Q(is_public=True))
        
        photos = Photo.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        ).filter(Q(album__user=request.user) | Q(album__is_public=True))
        
        templates = AlbumTemplate.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
        
        return Response({
            'albums': AlbumSerializer(albums, many=True).data,
            'photos': PhotoSerializer(photos, many=True).data,
            'templates': AlbumTemplateSerializer(templates, many=True).data,
        })
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Экспортировать альбомы в Excel"""
        resource = AlbumResource()
        dataset = resource.export(Album.objects.filter(user=request.user))
        
        response = HttpResponse(
            dataset.export('xlsx'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="albums.xlsx"'
        return response
    
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """Экспортировать альбом в PDF"""
        album = self.get_object()
        
        if album.user != request.user and not album.is_public:
            return Response(
                {'error': 'Нет доступа'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        title = Paragraph(f"<b>{album.title}</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        info = f"Автор: {album.user.username}<br/>Описание: {album.description}<br/>Фотографий: {album.photos.count()}"
        elements.append(Paragraph(info, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        photo_data = [['№', 'Название', 'Размер', 'Дата']]
        for i, photo in enumerate(album.photos.all(), 1):
            photo_data.append([
                str(i),
                photo.title,
                f"{photo.file_size / 1024 / 1024:.2f} МБ",
                photo.uploaded_at.strftime('%d.%m.%Y')
            ])
        
        if len(photo_data) > 1:
            table = Table(photo_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="album_{album.id}.pdf"'
        return response


class PhotoViewSet(ModelViewSet):
    serializer_class = PhotoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PhotoFilterSet
    search_fields = ['title', 'description', 'album__title']
    ordering_fields = ['uploaded_at', 'file_size']
    
    def get_queryset(self):
        return Photo.objects.select_related('album').filter(
            Q(album__user=self.request.user) | Q(album__is_public=True)
        )
    
    def perform_create(self, serializer):
        """Валидация загрузки фотографий"""
        album_id = self.request.data.get('album')
        album = get_object_or_404(Album, id=album_id)
        
        if album.user != self.request.user:
            raise serializers.ValidationError('Нельзя добавлять фото в чужой альбом')
        
        if album.photos.count() >= 100:
            raise serializers.ValidationError('Макс 100 фотографий в альбоме')
        
        file_size = self.request.FILES['image'].size
        if file_size > 10 * 1024 * 1024:
            raise serializers.ValidationError('Максимальный размер файла: 10 МБ')
        
        allowed_formats = ['jpg', 'jpeg', 'png', 'webp']
        file_name = self.request.FILES['image'].name
        file_ext = file_name.split('.')[-1].lower()
        if file_ext not in allowed_formats:
            raise serializers.ValidationError(
                f'Разрешенные форматы: {", ".join(allowed_formats)}'
            )
        
        serializer.save(album=album, file_size=file_size)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def edit(self, request, pk=None):
        """Редактировать фото"""
        photo = self.get_object()
        
        if photo.album.user != request.user:
            return Response(
                {'error': 'Только владелец может редактировать'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        brightness = request.data.get('brightness', 0)
        contrast = request.data.get('contrast', 0)
        saturation = request.data.get('saturation', 0)
        
        if not (-100 <= brightness <= 100):
            return Response(
                {'error': 'Brightness должна быть от -100 до 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not (-100 <= contrast <= 100):
            return Response(
                {'error': 'Contrast должна быть от -100 до 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not (-100 <= saturation <= 100):
            return Response(
                {'error': 'Saturation должна быть от -100 до 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        photo_edit, _ = PhotoEdit.objects.get_or_create(photo=photo)
        photo_edit.brightness = brightness
        photo_edit.contrast = contrast
        photo_edit.saturation = saturation
        photo_edit.save()
        
        return Response(PhotoEditSerializer(photo_edit).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reset_edits(self, request, pk=None):
        """Сбросить редактирование"""
        photo = self.get_object()
        
        if photo.album.user != request.user:
            return Response(
                {'error': 'Только владелец может сбросить редактирование'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        PhotoEdit.objects.filter(photo=photo).delete()
        return Response({'status': 'Edits reset'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reorder(self, request, pk=None):
        """Изменить порядок фото"""
        photo = self.get_object()
        
        if photo.album.user != request.user:
            return Response(
                {'error': 'Только владелец может менять порядок'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_order = request.data.get('order_index')
        photo.order_index = new_order
        photo.save()
        return Response(PhotoSerializer(photo).data)
    
    @action(detail=False, methods=['get'])
    def high_quality_photos(self, request):
        """Q ЗАПРОС 3: Поиск фото для тегов
        Фото с высоким разрешением И хорошим качеством, НЕ уже использованные"""
        photos = Photo.objects.filter(
            Q(dimensions__contains='1920') | Q(dimensions__contains='2048'),
            file_size__gt=1024*1024
        ).filter(
            Q(album__user=request.user) | Q(album__is_public=True)
        )
        
        return Response(PhotoSerializer(photos, many=True).data)


class AlbumTemplateViewSet(ModelViewSet):
    queryset = AlbumTemplate.objects.all()
    serializer_class = AlbumTemplateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['template_type', 'is_premium']
    search_fields = ['name', 'description']
    
    @action(detail=False, methods=['get'])
    def template_recommendations(self, request):
        """МЕТОД 2: Рекомендации шаблонов на основе типа фото"""
        templates = AlbumTemplate.objects.filter(is_premium=False).order_by('?')[:5]
        return Response(AlbumTemplateSerializer(templates, many=True).data)


class AlbumPageViewSet(ModelViewSet):
    serializer_class = AlbumPageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['album']
    
    def get_queryset(self):
        return AlbumPage.objects.select_related('album')


class PhotoEditViewSet(ModelViewSet):
    serializer_class = PhotoEditSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return PhotoEdit.objects.select_related('photo')
