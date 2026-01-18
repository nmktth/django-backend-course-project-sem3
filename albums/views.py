from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomUserLoginForm, CustomUserUpdateForm
from .models import User
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
import uuid
from django.http import HttpResponse

from .models import Album, Photo, AlbumTemplate, AlbumPage, PhotoEdit
from .serializers import (
    AlbumDetailSerializer, AlbumListSerializer, AlbumCreateSerializer,
    PhotoSerializer, AlbumTemplateSerializer, AlbumPageSerializer,
    PhotoEditSerializer
)

def register(request):
    if request.user.is_authenticated:
        return redirect('albums:profile')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) #Берём данные, что нам дал пользователь и проверяем на валидность
        if form.is_valid():
            user = form.save() #Сохраняем в нашей бд 
            login(request, user, backend='django.contrib.backends.ModelBackend') #Логиним
            return redirect('albums:profile')
    else:
        form = CustomUserCreationForm() #Выводим пустую форму в случае ошибки
        
    return render(request, 'albums/register.html', {'form': form})
    

def login_view(request):
    if request.user.is_authenticated:
        return redirect('albums:profile')
    if request.method == 'POST':
        form = CustomUserLoginForm(request=request, data=request.POST)
        if form.is_valid(): #Проверяем валидность
            user = form.get_user() #Берём нашего юзера и логиним его
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('albums:profile')
    else:
        form = CustomUserLoginForm()

    return render(request, 'albums/login.html', {'form': form})


@login_required
def profile_views(request):
    albums = request.user.albums.all()
    templates = AlbumTemplate.objects.filter(is_premium=False)
    
    context = {
        'user': request.user,
        'albums': albums,
        'templates': templates,
        'user_stats': {
            'total_albums': albums.count(),
            'is_premium': request.user.is_premium
        }
    }
    return render(request, 'albums/profile.html', context)

@login_required
def my_albums_html(request):
    """HTML список моих альбомов для HTMX"""
    albums = request.user.albums.all()
    return render(request, 'albums/partials/albums_list.html', {
        'albums': albums
    })

@login_required
def upload_photo(request, album_id):
    """Загрузка фото в альбом"""
    try:
        album = Album.objects.get(id=album_id, user=request.user)
    except Album.DoesNotExist:
        return redirect('albums:profile')
    
    if request.method == 'POST':
        files = request.FILES.getlist('photos')
        for file in files:
            Photo.objects.create(
                album=album,
                image=file,
                title=file.name
            )
        return redirect('albums:album_detail', album_id=album_id)
    
    return render(request, 'albums/upload_photo.html', {'album': album})


@login_required
def albums_list_partial(request):
    """Partial для списка альбомов в профиле"""
    albums = request.user.albums.all().select_related('layout_template')[:6]
    serializer = AlbumListSerializer(albums, many=True)
    return render(request, 'albums/partials/albums_list.html', {
        'albums': albums
    })


@login_required
def create_album_form(request):
    """Форма создания альбома для HTMX"""
    templates = AlbumTemplate.objects.filter(is_premium=False)[:5]  # бесплатные
    return render(request, 'albums/partials/create_album_form.html', {
        'templates': templates
    })
    

@login_required
def create_quick_album(request):
    if request.method == 'POST':
        base_title = request.POST.get('title', 'Новый альбом')
        description = request.POST.get('description', '')

        # Генерация уникального названия
        title = base_title
        counter = 1
        while Album.objects.filter(user=request.user, title=title).exists():
            title = f"{base_title} ({counter})"
            counter += 1

        album = Album.objects.create(
            user=request.user,
            title=title,
            description=description
        )
        return redirect('albums:profile')

    return render(request, 'albums/partials/create_album_form.html')

@login_required
def album_detail(request, album_id):
    album = Album.objects.get(id=album_id)
    photos = album.photos.all().order_by('order_index')
    pages = album.pages.all()
    return render(request, 'albums/album_detail.html', {
        'album': album,
        'photos': photos,
        'pages': pages
    })



# utils.py или прямо в views.py
def create_album_pages(album, page_size=4):
    """Создает страницы и распределяет фото по ним"""
    album.pages.all().delete()
    photos = list(album.photos.all().order_by('order_index'))
    template = album.layout_template

    for i in range(0, len(photos), page_size):
        page_number = i // page_size + 1
        page = AlbumPage.objects.create(
            album=album,
            page_number=page_number,
            template=template,
            thumbnail=template.thumbnail if template else None
        )
        for photo in photos[i:i + page_size]:
            photo.page = page
            photo.save()



@login_required
def upload_photo(request, album_id):
    """Загрузка фото в альбом"""
    try:
        album = Album.objects.get(id=album_id, user=request.user)
    except Album.DoesNotExist:
        return redirect('albums:profile')
    
    if request.method == 'POST':
        files = request.FILES.getlist('photos')
        for file in files:
            Photo.objects.create(
                album=album,
                image=file,
                title=file.name
            )
        
        # ✅ создаём страницы на основе фото
        create_album_pages(album, page_size=4)  # например, 4 фото на страницу
        
        return redirect('albums:album_detail', album_id=album_id)
    
    return render(request, 'albums/upload_photo.html', {'album': album})


def update_album_pages(album, page_size=4):
    """Разбивает фото альбома на страницы"""
    photos = list(album.photos.all().order_by('order_index'))
    
    # Удаляем старые страницы
    album.pages.all().delete()
    
    # Создаём новые страницы
    for i in range(0, len(photos), page_size):
        page_number = i // page_size + 1
        AlbumPage.objects.create(album=album, page_number=page_number)

def album_template_css(request, template_id):
    try:
        template = AlbumTemplate.objects.get(id=template_id)
        return HttpResponse(template.css_styles, content_type='text/css')
    except AlbumTemplate.DoesNotExist:
        return HttpResponse("", content_type='text/css')


@login_required
def account_details(request):
    user = User.objects.get(id=request.user.id)
    return render(request, 'albums/partials/account_details.html',
                  {'user': user})


@login_required
def edit_account_details(request):
    form = CustomUserUpdateForm(instance=request.user)
    return render(request, 'albums/partials/edit_account_details.html', 
                  {'user': request.user, 'form': form})


@login_required
def update_account_details(request):
    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.clean()
            user.save()
            return render(request, 'albums/partials/account_details.html', {'user': user})
        else:
            return render(request, 'albums/partials/edit_account_details.html', {'user': request.user, 'form': form})
    return render(request, 'albums/partials/account_details.html', {'user': request.user})
     
       
def logout_view(request):
    logout(request)
    return redirect('albums:register')

class AlbumViewSet(viewsets.ModelViewSet):
    """ViewSet для альбомов"""
    queryset = Album.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']
    filterset_fields = ['is_public', 'layout_template']
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от action"""
        if self.action == 'retrieve':
            return AlbumDetailSerializer
        elif self.action == 'create':
            return AlbumCreateSerializer
        elif self.action == 'list':
            return AlbumListSerializer
        return AlbumDetailSerializer
    
    def get_queryset(self):
        """Получить QuerySet для текущего пользователя"""
        user = self.request.user
        
        # Для list view: свои альбомы + публичные
        if self.action == 'list':
            if user.is_authenticated:
                return Album.objects.filter(
                    Q(user=user) | Q(is_public=True)
                ).select_related('layout_template', 'user').prefetch_related('photos')
            return Album.objects.filter(is_public=True).select_related('layout_template', 'user')
        
        # Для остальных: все с оптимизацией запросов
        return Album.objects.select_related(
            'layout_template', 'user', 'cover_photo'
        ).prefetch_related('photos', 'pages', 'comments')
    
    def perform_create(self, serializer):
        """Создание альбома с текущим пользователем"""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Обновление альбома"""
        if serializer.instance.user != self.request.user:
            raise serializers.ValidationError('Вы не можете изменить чужой альбом')
        serializer.save()
    
    def perform_destroy(self, instance):
        """Удаление альбома"""
        if instance.user != self.request.user:
            raise serializers.ValidationError('Вы не можете удалить чужой альбом')
        instance.delete()
    
    # ========== CUSTOM ACTIONS ==========
    
    @action(methods=['GET'], detail=False)
    def my_albums(self, request):
        """GET /albums/my_albums/ - Мои альбомы"""
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        albums = request.user.albums.all().select_related('layout_template').prefetch_related('photos')
        
        # Фильтрация
        is_public = request.query_params.get('is_public')
        if is_public is not None:
            albums = albums.filter(is_public=is_public.lower() == 'true')
        
        page = self.paginate_queryset(albums)
        if page is not None:
            serializer = AlbumListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AlbumListSerializer(albums, many=True)
        return Response(serializer.data)
    
    @action(methods=['GET'], detail=False)
    def user_stats(self, request):
        """GET /albums/user_stats/ - Статистика пользователя"""
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        albums = user.albums.all()
        
        # Статистика
        total_albums = albums.count()
        total_photos = sum(album.photos.count() for album in albums)
        total_size_bytes = albums.aggregate(total=Sum('photos__file_size'))['total'] or 0
        total_size_mb = round(total_size_bytes / 1024 / 1024, 2)
        
        # Популярные шаблоны
        popular_templates = albums.values(
            'layout_template__name'
        ).annotate(count=Count('id')).order_by('-count')[:5]
        
        # Недавно обновленные альбомы
        recent_albums = albums.filter(
            updated_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        return Response({
            'total_albums': total_albums,
            'total_photos': total_photos,
            'total_size_mb': total_size_mb,
            'recent_albums': recent_albums,
            'popular_templates': list(popular_templates),
            'is_premium': user.is_premium,  # ✅ ТВОЁ поле is_premium
            'premium_until': user.premium_until
        })
    
    @action(methods=['GET'], detail=False)
    def popular(self, request):
        """GET /albums/popular/ - Популярные публичные альбомы"""
        albums = Album.objects.filter(
            is_public=True,
            photos__isnull=False
        ).annotate(
            photo_count=Count('photos')
        ).filter(
            photo_count__gte=3
        ).distinct().order_by('-updated_at')[:10]
        
        serializer = AlbumListSerializer(albums, many=True)
        return Response(serializer.data)
    
    @action(methods=['POST'], detail=True)
    def publish(self, request, pk=None):
        """POST /albums/{id}/publish/ - Опубликовать альбом"""
        album = self.get_object()
        
        if album.user != request.user:
            return Response(
                {'detail': 'Вы не можете опубликовать чужой альбом'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if album.photos.count() < 3:
            return Response(
                {'detail': 'Альбом должен содержать минимум 3 фотографии'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        album.is_public = True
        album.save()
        serializer = AlbumDetailSerializer(album)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=['POST'], detail=True)
    def unpublish(self, request, pk=None):
        """POST /albums/{id}/unpublish/ - Скрыть альбом"""
        album = self.get_object()
        
        if album.user != request.user:
            return Response(
                {'detail': 'Вы не можете изменить чужой альбом'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        album.is_public = False
        album.save()
        serializer = AlbumDetailSerializer(album)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=['POST'], detail=True)
    def apply_template(self, request, pk=None):
        """POST /albums/{id}/apply_template/ - Применить шаблон"""
        album = self.get_object()
        
        if album.user != request.user:
            return Response(
                {'detail': 'Вы не можете изменить чужой альбом'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        template_id = request.data.get('template_id')
        if not template_id:
            return Response(
                {'detail': 'template_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            template = AlbumTemplate.objects.get(id=template_id)
        except AlbumTemplate.DoesNotExist:
            return Response(
                {'detail': 'Шаблон не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ✅ Проверяем ТВОЁ поле is_premium
        if template.is_premium and not request.user.is_premium:
            return Response(
                {'detail': 'Этот шаблон доступен только для премиум пользователей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        album.layout_template = template
        album.save()
        serializer = AlbumDetailSerializer(album)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PhotoViewSet(viewsets.ModelViewSet):
    """ViewSet для фотографий"""
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['uploaded_at', 'order_index']
    ordering = ['order_index', '-uploaded_at']
    filterset_fields = ['album']
    
    def get_queryset(self):
        """Получить фото только из доступных альбомов"""
        user = self.request.user
        if user.is_authenticated:
            return Photo.objects.filter(
                Q(album__user=user) | Q(album__is_public=True)
            ).select_related('album')
        return Photo.objects.filter(album__is_public=True).select_related('album')
    
    @action(methods=['POST'], detail=True)
    def reorder(self, request, pk=None):
        """POST /photos/{id}/reorder/ - Изменить порядок"""
        photo = self.get_object()
        new_order = request.data.get('order_index')
        
        if new_order is None:
            return Response(
                {'detail': 'order_index required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        photo.order_index = new_order
        photo.save()
        serializer = self.get_serializer(photo)
        return Response(serializer.data)
    
    @action(methods=['POST'], detail=True)
    def add_edit(self, request, pk=None):
        """POST /photos/{id}/add_edit/ - Добавить редактирование"""
        photo = self.get_object()
        serializer = PhotoEditSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(photo=photo)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlbumTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для шаблонов (только чтение)"""
    queryset = AlbumTemplate.objects.all()
    serializer_class = AlbumTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    filterset_fields = ['template_type', 'is_premium']
    
    def get_queryset(self):
        """✅ Проверяем ТВОЁ поле is_premium из User"""
        user = self.request.user
        
        # Если пользователь премиум, показываем все шаблоны
        if user.is_authenticated and user.is_premium:
            return AlbumTemplate.objects.all()
        
        # Иначе только бесплатные
        return AlbumTemplate.objects.filter(is_premium=False)
    
    @action(methods=['GET'], detail=False)
    def available(self, request):
        """GET /templates/available/ - Доступные для меня шаблоны"""
        templates = self.get_queryset()
        serializer = AlbumTemplateSerializer(templates, many=True)
        return Response(serializer.data)


class AlbumPageViewSet(viewsets.ModelViewSet):
    """ViewSet для страниц альбома"""
    queryset = AlbumPage.objects.all()
    serializer_class = AlbumPageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['album']
    ordering_fields = ['page_number']
    ordering = ['page_number']


class PhotoEditViewSet(viewsets.ModelViewSet):
    """ViewSet для редактирования фото"""
    queryset = PhotoEdit.objects.all()
    serializer_class = PhotoEditSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['photo']
    ordering_fields = ['created_at']
    ordering = ['-created_at']