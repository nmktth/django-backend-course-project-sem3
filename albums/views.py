import uuid
import json
from typing import Any, cast

from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.generic import ListView
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpRequest
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, permissions, status, generics, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token


from .models import Album, Photo, Collage, BugReport, UserProfile
from .forms import StyledUserCreationForm, UserForm, ProfileForm
from .serializers import (
    AlbumSerializer,
    PhotoSerializer,
    CollageSerializer,
    UserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    BugReportSerializer,
)
from .utils import create_collage_image, export_queryset_to_excel


class UserOwnedMixin:
    """Миксин для ViewSet'ов с фильтрацией по текущему пользователю."""

    user_field = "user"  # Поле для фильтрации
    request: Any
    queryset: Any

    def get_queryset(self):
        return self.queryset.filter(**{self.user_field: self.request.user})

    def perform_create(self, serializer):
        serializer.save(**{self.user_field: self.request.user})


# ==================== AUTH VIEWS ====================


class UserRegistrationView(generics.CreateAPIView):
    """Регистрация нового пользователя."""

    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Автоматически создаём токен при регистрации
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "user": UserProfileSerializer(user).data,
                "token": token.key,
                "message": "Регистрация успешна!",
            },
            status=status.HTTP_201_CREATED,
        )


class UserLogoutView(APIView):
    """Выход пользователя (удаление токена)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Удаляем токен пользователя
        request.user.auth_token.delete()
        return Response({"message": "Вы успешно вышли из системы."}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Просмотр и обновление профиля текущего пользователя."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """Смена пароля текущего пользователя."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Обновляем токен после смены пароля
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        return Response(
            {"message": "Пароль успешно изменён.", "token": new_token.key},
            status=status.HTTP_200_OK,
        )


class AlbumViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # 5 variants of filtering
    filterset_fields = {
        "is_public": ["exact"],
        "title": ["icontains"],
        "created_at": ["gte", "lte", "year"],
    }
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title", "updated_at"]

    @action(detail=False, methods=["get"])
    def advanced_search(self, request):
        """
        Complex Search Action (Requirement 1):
        Uses Q objects with OR (|), AND (&), and NOT (~).
        Query params: 'query' (text), 'mode' (public/private).
        """
        query = request.query_params.get("query", "")
        mode = request.query_params.get("mode", "all")

        # Base: User's albums OR Public albums
        # (user=me) | (is_public=True)
        base_condition = Q(user=request.user) | Q(is_public=True)

        if query:
            # Complex logic:
            # (Title contains query OR Description contains query) AND NOT (Title="Untitled")
            text_condition = (Q(title__icontains=query) | Q(description__icontains=query)) & ~Q(
                title__iexact="Untitled"
            )

            # Combine: Base AND Text
            final_query = base_condition & text_condition
        else:
            final_query = base_condition

        # Additional complexity with NOT
        if mode == "private_only":
            # AND NOT is_public
            final_query = final_query & ~Q(is_public=True)

        albums = Album.objects.filter(final_query).distinct()
        # albums = Album.objects.filter(final_query).select_related('user').distinct()
        serializer = self.get_serializer(albums, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def user_albums_stats(self, request):
        """Статистика альбомов пользователя (Section 9.1)."""
        albums = self.get_queryset()
        total_albums = albums.count()
        # Mocking size because we don't store individual photo sizes in DB perfectly aligned with reqs
        total_photos = Photo.objects.filter(album__in=albums).count()
        return Response(
            {
                "total_albums": total_albums,
                "total_photos": total_photos,
                "message": "Stats retrieved",
            }
        )

    @action(detail=False, methods=["get"])
    def template_recommendations(self, request):
        """Рекомендации шаблонов (Section 9.2)."""
        # Mock logic
        return Response(
            {
                "recommended": ["wedding", "travel", "simple"],
                "reason": "Based on your recent photos",
            }
        )

    @action(methods=["POST"], detail=True)
    def duplicate_album(self, request, pk=None):
        """Создать копию альбома (Section 9.3)."""
        # 1. Limit check
        if Album.objects.filter(user=request.user).count() >= 20:
            return Response(
                {"error": "Вы достигли лимита в 20 альбомов."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        original = self.get_object()

        # 2. Unique Title Logic
        base_title = f"Copy of {original.title}"
        title = base_title
        counter = 1
        while Album.objects.filter(user=request.user, title=title).exists():
            title = f"{base_title} ({counter})"
            counter += 1

        new_album = Album.objects.create(
            user=request.user, title=title, description=original.description
        )
        # Copy photos
        for photo in original.photos.all():
            Photo.objects.create(
                album=new_album,
                image=photo.image,
                is_favorite=photo.is_favorite,
            )
        serializer = self.get_serializer(new_album)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=True)
    def generate_share_link(self, request, pk=None):
        """Сгенерировать ссылку (Section 9.4)."""
        return Response({"link": f"https://example.com/share/{uuid.uuid4()}", "expires_in": "24h"})

    @action(methods=["POST"], detail=True)
    def publish(self, request, pk=None):
        """Публикация альбома (Section 2, 3.5)."""
        album = self.get_object()
        if album.photos.count() < 3:
            return Response(
                {"error": "Альбом должен содержать минимум 3 фотографии."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "Album published (mocked)"})

    @action(methods=["POST"], detail=True)
    def share(self, request, pk=None):
        """Поделиться альбомом (Section 2)."""
        return Response({"status": "Shared"})

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """Экспорт списка альбомов в Excel (Section 6, 7)."""
        headers = [
            "Название",
            "Кол-во фото",
            "Дата создания",
            "Шаблон",
            "Статус",
            "Размер",
            "Заполненность",
            "Тип",
            "Рейтинг",
            "Активность",
        ]

        def dehydrate_album_size(obj):
            return "15.5 МБ"

        def dehydrate_completion_status(obj):
            photo_count = obj.photos.count()  # type: ignore
            if photo_count == 0:
                return "Пустой"
            elif photo_count < 10:
                return "Мало фото"
            else:
                return "Заполнен"

        def dehydrate_template_type(obj):
            layout = getattr(obj, "layout_template", "standard")
            colors = {"wedding": "💒", "travel": "✈️", "portrait": "👤", "family": "👪"}
            return f"{colors.get(layout, '📁')} {layout}"

        def dehydrate_album_rating(obj):
            views = getattr(obj, "views_count", 0)
            if views > 1000:
                return "Популярный"
            elif views > 100:
                return "Средний"
            else:
                return "Новый"

        def dehydrate_recent_activity(obj):
            # Section 7.5
            if not obj.updated_at:
                return "Неактивный"
            days_ago = (timezone.now() - obj.updated_at).days
            if days_ago == 0:
                return "Сегодня"
            elif days_ago <= 7:
                return f"{days_ago} дней назад"
            else:
                return "Неактивный"

        def extract_row(album):
            return [
                album.title,
                str(album.photos.count()),
                album.created_at.strftime("%Y-%m-%d"),
                "Standard",  # Mock template
                "Draft",  # Mock status
                dehydrate_album_size(album),
                dehydrate_completion_status(album),
                dehydrate_template_type(album),
                dehydrate_album_rating(album),
                dehydrate_recent_activity(album),
            ]

        return export_queryset_to_excel(
            queryset=self.get_queryset(),
            headers=headers,
            row_extractor=extract_row,
            sheet_title="Albums Export",
            filename_prefix="my_albums",
        )

    @action(detail=True, methods=["post"], url_path="upload-photos")
    def upload_photos(self, request, pk=None):
        album = self.get_object()
        images = request.FILES.getlist("images")

        if not images:
            return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

        created_photos = []
        for image in images:
            photo = Photo.objects.create(album=album, image=image)
            created_photos.append(photo)

        return Response(
            {"status": "Photos uploaded", "count": len(created_photos)},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="generate-collage")
    def generate_collage(self, request, pk=None):
        album = self.get_object()
        photos = album.photos.all()
        favorites = photos.filter(is_favorite=True)
        if favorites.exists():
            photos_to_use = favorites
        else:
            photos_to_use = photos

        if not photos_to_use.exists():
            return Response(
                {"error": "No photos in album to generate collage"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        collage_file = create_collage_image(photos_to_use)

        if collage_file:
            collage = Collage(album=album)
            collage.image.save(f"collage_{uuid.uuid4()}.jpg", collage_file)
            serializer = CollageSerializer(collage)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"error": "Failed to generate collage"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PhotoViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    """Управление фотографиями (удаление, просмотр, пометка избранным)."""

    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    pagination_class = PageNumberPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["album", "created_at", "is_favorite"]
    ordering_fields = ["created_at", "file_size"]  # file_size mock
    user_field = "album__user"  # Переопределяем поле фильтрации

    @action(detail=False, methods=["get"])
    def complex_filter(self, request):
        """
        Сложная фильтрация фото (Q-запрос из задания):
        Все фото пользователя ИЛИ (Избранные фото из НЕ приватных альбомов).
        """
        # (is_favorite=True) & ~Q(album__is_public=False) -> Избранные в публичных альбомах
        # | Q(album__user=request.user) -> Или все мои фото
        query = (Q(is_favorite=True) & ~Q(album__is_public=False)) | Q(album__user=request.user)

        photos = Photo.objects.filter(query).distinct().order_by("-created_at")

        page = self.paginate_queryset(photos)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(photos, many=True)
        return Response(serializer.data)

    @action(methods=["POST"], detail=True)
    def reorder(self, request, pk=None):
        """Изменить порядок (Section 2)."""
        # Logic to change order_index would go here
        return Response({"status": "Reordered"})

    @action(methods=["POST"], detail=True)
    def edit(self, request, pk=None):
        """Редактировать фото (Section 2). Validation 3.3"""
        # Mocking edit logic
        # Filters: -100 to 100 validation
        filters_data = request.data.get("filters", {})
        for k, v in filters_data.items():
            try:
                val = int(v)
                if not (-100 <= val <= 100):
                    return Response(
                        {"error": f"Filter {k} out of bounds"}, status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                pass

        return Response({"status": "Edited", "filters": filters_data})

    @action(methods=["POST"], detail=True)
    def reset_edits(self, request, pk=None):
        """Сбросить редактирование (Section 2)."""
        return Response({"status": "Edits reset"})

    def create(self, request, *args, **kwargs):
        """Запрещаем прямое создание фото (через POST /photos/)."""
        return Response(
            {"detail": "Используйте /api/albums/{id}/upload-photos/ для загрузки фотографий."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class BugReportViewSet(UserOwnedMixin, viewsets.ModelViewSet):
    queryset = BugReport.objects.all()
    serializer_class = BugReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Админ видит все, пользователь — только свои
        if self.request.user.is_staff:
            return BugReport.objects.all()
        return super().get_queryset()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAdminUser],
        url_path="export-excel",
    )
    def export_excel(self, request):
        """Экспорт баг-репортов в Excel (только для админа)."""
        headers = ["ID", "User", "Title", "Description", "Status", "Created At"]

        def extract_row(report):
            return [
                str(report.id),
                report.user.username,
                report.title,
                report.description,
                report.status,
                report.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]

        return export_queryset_to_excel(
            queryset=BugReport.objects.all(),
            headers=headers,
            row_extractor=extract_row,
            sheet_title="Bug Reports",
            filename_prefix="bug_reports",
        )


# ==================== WEB AUTH VIEWS ====================


def register_view(request):
    if request.method == "POST":
        form = StyledUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = StyledUserCreationForm()
    return render(request, "auth/register.html", {"form": form})


@method_decorator(login_required, name="dispatch")
class DashboardView(ListView):
    model = Album
    template_name = "dashboard/index.html"
    context_object_name = "albums"

    def get_queryset(self):
        queryset = Album.objects.filter(user=self.request.user)

        # Search
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))

        # Status Filter
        status_filter = self.request.GET.get("status")
        if status_filter == "public":
            queryset = queryset.filter(is_public=True)
        elif status_filter == "private":
            queryset = queryset.filter(is_public=False)

        # Sorting
        ordering = self.request.GET.get("ordering", "-created_at")
        allowed_ordering = ["created_at", "-created_at", "title", "-title"]
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_ordering"] = self.request.GET.get("ordering", "-created_at")
        return context


@login_required
def create_album_view(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        photos = request.FILES.getlist("photos")

        # Check for file size
        max_size = 10 * 1024 * 1024  # 10 MB
        for photo in photos:
            if photo.size > max_size:
                return render(request, "pages/upload_error.html")

        album = Album.objects.create(user=request.user, title=title, description=description)

        for photo in photos:
            Photo.objects.create(album=album, image=photo)

        return redirect("dashboard")

    return render(request, "dashboard/create_album.html")


@login_required
def edit_profile_view(request):
    try:
        request.user.profile
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Ваш профиль был успешно обновлен!")
            return redirect("profile")
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки ниже.")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    return render(
        request, "dashboard/profile.html", {"user_form": user_form, "profile_form": profile_form}
    )


@login_required
def profile_view(request):
    try:
        request.user.profile
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user)

    return render(request, "dashboard/profile_view.html", {"user": request.user})


def album_detail_view(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    album = (
        Album.objects
        .select_related('user')  #Владелец альбома
        .prefetch_related('photos', 'editors')  #Фото и редакторы
        .get(pk=pk)
    )
    
    #Уже в памяти, без доп запросов
    is_owner = request.user.is_authenticated and album.user == request.user
    is_editor = request.user.is_authenticated and (
        is_owner or album.editors.filter(id=request.user.id).exists()
    )

    if not is_editor and not album.is_public:
        # If user is not owner/editor and album is not public, deny access
        if not request.user.is_authenticated:
            return redirect("login")
        return HttpResponseForbidden("You do not have permission to view this album.")

    photos = album.photos.all()  # type: ignore

    context = {
        "album": album,
        "photos": photos,
        "is_owner": is_owner,
        "is_editor": is_editor,
        "absolute_uri": request.build_absolute_uri(),  # For the share link
    }
    return render(request, "dashboard/album_detail.html", context)


@login_required
def add_photos_view(request, pk):
    album = get_object_or_404(Album, pk=pk)

    # Permission check: Owner or Editor
    is_owner = album.user == request.user
    is_editor = album.editors.filter(id=cast(User, request.user).id).exists()  # type: ignore

    if not (is_owner or is_editor):
        return HttpResponseForbidden("You do not have permission to add photos to this album.")

    if request.method == "POST":
        photos = request.FILES.getlist("photos")
        if photos:
            # Check for file size
            max_size = 10 * 1024 * 1024  # 10 MB
            for photo in photos:
                if photo.size > max_size:
                    return render(request, "pages/upload_error.html")

            for photo in photos:
                Photo.objects.create(album=album, image=photo)
            messages.success(request, f"Added {len(photos)} photos.")
        else:
            messages.warning(request, "No photos selected.")

    return redirect("album_detail", pk=pk)


@login_required
def add_collaborator_view(request, pk):
    album = get_object_or_404(Album, pk=pk)

    # Permission check: Owner only
    if album.user != request.user:
        return HttpResponseForbidden("Only the album owner can add collaborators.")

    if request.method == "POST":
        username = request.POST.get("username")
        try:
            user = User.objects.get(username=username)
            if user == request.user:
                messages.error(request, "You are already the owner.")
            elif album.editors.filter(id=user.id).exists():  # type: ignore
                messages.info(request, f"{user.username} is already an editor.")
            else:
                album.editors.add(user)
                messages.success(request, f"Added {user.username} as editor.")
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' not found.")

    return redirect("album_detail", pk=pk)


@login_required
def remove_collaborator_view(request, pk, user_id):
    album = get_object_or_404(Album, pk=pk)

    # Permission check: Owner only
    if album.user != request.user:
        return HttpResponseForbidden("Only the album owner can remove collaborators.")

    if request.method == "POST":
        user_to_remove = get_object_or_404(User, pk=user_id)
        album.editors.remove(user_to_remove)
        messages.success(request, f"Removed access for {user_to_remove.username}.")

    return redirect("album_detail", pk=pk)


@login_required
def delete_album_view(request, pk):
    album = get_object_or_404(Album, pk=pk)

    # Permission check: Owner only
    if album.user != request.user:
        return HttpResponseForbidden("Only the album owner can delete the album.")

    if request.method == "POST":
        album.delete()
        messages.success(request, "Album deleted successfully.")
        return redirect("dashboard")

    return redirect("album_detail", pk=pk)


@login_required
def toggle_public_view(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    album = get_object_or_404(Album, pk=pk)

    if album.user != request.user:
        return HttpResponseForbidden("You are not the owner of this album.")

    if request.method == "POST":
        album.is_public = not album.is_public
        album.save()
        status_msg = "published" if album.is_public else "private"
        messages.success(request, f"Album is now {status_msg}.")

    return redirect("album_detail", pk=pk)


def generate_collage_view(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    album = get_object_or_404(Album, pk=pk)

    # Check permissions (same as detail view)
    is_owner = request.user.is_authenticated and album.user == request.user
    is_editor = request.user.is_authenticated and (
        is_owner or album.editors.filter(id=request.user.id).exists()  # type: ignore
    )

    if not is_editor and not album.is_public:
        if not request.user.is_authenticated:
            return redirect("login")
        return HttpResponseForbidden("You do not have permission to view this album.")

    photos = album.photos.all()  # type: ignore
    if not photos:
        return HttpResponse("No photos in album", status=404)

    collage_file = create_collage_image(photos, output_format="PNG")

    if not collage_file:
        return HttpResponse("Error creating collage", status=500)

    # Save collage to DB
    filename = f"collage_{album.id}_{uuid.uuid4().hex[:8]}.png"
    collage = Collage(album=album)
    collage.image.save(filename, collage_file, save=True)

    # Re-open the saved file to return in response
    response = HttpResponse(collage.image.open(), content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def share_photo_view(request, pk):
    """
    Генерация ссылки для шаринга отдельной фотографии.
    """
    photo = get_object_or_404(Photo, pk=pk)

    # Check permission (owner or editor of the album)
    album = photo.album
    if album.user != request.user and request.user not in album.editors.all():
        return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)

    if request.method == "POST":
        data = request.POST
        action = data.get("action")

        # If calling via fetch with JSON body
        if not action and request.body:
            try:
                body = json.loads(request.body)
                action = body.get("action")
            except (json.JSONDecodeError, ValueError):
                pass

        if action == "generate":
            if not photo.public_token:
                photo.public_token = uuid.uuid4()
                photo.save()

            link = request.build_absolute_uri(reverse("public_photo", args=[photo.public_token]))
            return JsonResponse({"status": "ok", "link": link})

        elif action == "disable":
            photo.public_token = None
            photo.save()
            return JsonResponse({"status": "ok", "message": "Link disabled"})

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


def public_photo_view(request, token):
    """
    Публичный просмотр фотографии по токену.
    """
    photo = get_object_or_404(Photo, public_token=token)

    context = {"photo": photo, "album": photo.album, "download_name": f"photo_{photo.id}.jpg"}
    return render(request, "public_photo.html", context)
