import os
import uuid
from typing import Any

from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from simple_history.models import HistoricalRecords


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь"
    )
    avatar = CloudinaryField(verbose_name="Аватар", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, verbose_name="О себе")
    location = models.CharField(max_length=30, blank=True, verbose_name="Местоположение")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")

    def __str__(self):
        return f"{self.user.username}'s profile"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        ordering = ["user__username"]


def get_album_media_path(user_id: Any, album_id: Any, subfolder: str, filename: str) -> str:
    """Общая функция для формирования путей медиафайлов альбома."""
    # Укорачиваем имя файла, чтобы избежать проблем с длиной пути, даже с увеличенным лимитом
    name, ext = os.path.splitext(filename)
    if len(name) > 50:
        filename = f"{name[:50]}{ext}"

    return f"user_{user_id}/album_{album_id}/{subfolder}/{filename}"


def photo_directory_path(instance: Any, filename: str) -> str:
    """Путь для загрузки фотографий."""
    return get_album_media_path(instance.album.user.id, instance.album.id, "photos", filename)


def collage_directory_path(instance: Any, filename: str) -> str:
    """Путь для загрузки коллажей."""
    return get_album_media_path(instance.album.user.id, instance.album.id, "collages", filename)


class Album(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="albums", verbose_name="Пользователь"
    )
    editors = models.ManyToManyField(
        User, related_name="editable_albums", blank=True, verbose_name="Редакторы"
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    is_public = models.BooleanField(default=False, verbose_name="Публичный")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    class Meta:
        verbose_name = "Альбом"
        ordering = ["-created_at"]
        verbose_name_plural = "Альбомы"


class Photo(models.Model):
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="photos", verbose_name="Альбом"
    )
    image = models.ImageField(
        upload_to=photo_directory_path, max_length=500, verbose_name="Изображение"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_favorite = models.BooleanField(
        default=False, verbose_name="Избранное"
    )  # For 'best shots' feature
    public_token = models.UUIDField(
        editable=False,
        null=True,
        blank=True,
        unique=True,
        verbose_name="Публичный токен",
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"Photo {self.id} in {self.album.title}"

    class Meta:
        verbose_name = "Фотография"
        ordering = ["-created_at"]
        verbose_name_plural = "Фотографии"


class Collage(models.Model):
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="collages", verbose_name="Альбом"
    )
    image = models.ImageField(
        upload_to=collage_directory_path, max_length=500, verbose_name="Изображение"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Collage {self.id} for {self.album.title}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Коллаж"
        verbose_name_plural = "Коллажи"


class BugReport(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bug_reports",
        null=True,
        blank=True,
        verbose_name="Пользователь",
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(
        max_length=20,
        default="open",
        choices=[("open", "Open"), ("closed", "Closed")],
        verbose_name="Статус",
    )

    def __str__(self):
        return f"Bug: {self.title} ({self.status})"

        ordering = ["-created_at"]
    class Meta:
        verbose_name = "Сообщение об ошибке"
        verbose_name_plural = "Сообщения об ошибках"
