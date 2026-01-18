from django.db import models
from django.contrib.auth.models import AbstractUser, \
    BaseUserManager
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Вы забыли ввести почту!')
        if not username:
            raise ValueError('Вы забыли ввести юзернейм!')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(email=email, first_name=first_name,
                          last_name=last_name, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)


    def create_superuser(self, email, first_name, last_name, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_premium', True)
        extra_fields.setdefault('premium_until', None) 

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, first_name, last_name, username, password, **extra_fields)



class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=66)
    username = models.CharField(max_length=25, unique=True)
    first_name = models.CharField(max_length=25)
    last_name = models.CharField(max_length=25)
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    def __str__(self):
        return self.email
    
    def clean(self):
        for field in ['first_name', 'last_name', 'email', 'username']:
            value = getattr(self, field)
            if value:
                setattr(self, field, strip_tags(value)) #Хорошая защита от XSS атак, если в моделях и в форме, это двойная защита от проникновения вредоносного JS кода и т.д.


class AlbumTemplate(models.Model):
    """Шаблон альбома на основе CSS стилей"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    css_styles = models.TextField(
        default='',
        help_text='CSS, который будет применяться к страницам альбома'
    )
    thumbnail = models.ImageField(
        upload_to='templates/',
        null=True,
        blank=True,
        help_text='Мини-превью шаблона (например, маленькая картинка для выбора)'
    )
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Шаблон альбома'
        verbose_name_plural = 'Шаблоны альбомов'

    def __str__(self):
        return self.name



class Album(models.Model):
    """Фотоальбом"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cover_photo = models.ForeignKey(
        'Photo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='album_cover'
    )
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    layout_template = models.ForeignKey(
        AlbumTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='albums'
    )
    
    class Meta:
        unique_together = ('user', 'title')
        ordering = ['-created_at']
        verbose_name = 'Фотоальбом'
        verbose_name_plural = 'Фотоальбомы'
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        # Если шаблон не указан, автоматически ставим "Классический"
        if self.layout_template is None:
            self.layout_template = AlbumTemplate.objects.filter(name="Классический").first()
        super().save(*args, **kwargs)

    
    def clean(self):
        # Валидация: максимум 20 альбомов на пользователя
        if self.user.albums.exclude(pk=self.pk).count() >= 20:
            raise ValidationError('Максимум 20 альбомов на пользователя')
        
        # Валидация: проверка прав на премиум шаблон, используем is_premiun из юзера нашего кастомного
        if self.layout_template and self.layout_template.is_premium and not self.user.is_premium:
            raise ValidationError('Этот шаблон доступен только для премиум пользователей')
        
        # Валидация: уникальность названия в рамках пользователя
        duplicate = Album.objects.filter(
            user=self.user,
            title=self.title
        ).exclude(pk=self.pk)
        if duplicate.exists():
            raise ValidationError('У вас уже есть альбом с таким названием')


class Photo(models.Model):
    """Фотография"""
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='photos')
    page = models.ForeignKey(
        'AlbumPage',  # связь с моделью страницы
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='photos'
    )
    image = models.ImageField(
        upload_to='photos/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0)
    dimensions = models.CharField(max_length=20, blank=True)
    order_index = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order_index', 'uploaded_at']
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
    
    def __str__(self):
        return f"{self.title or self.image.name} ({self.album.title})"
    
    def clean(self):
        # Валидация: максимум 100 фото в альбоме
        if self.album.photos.exclude(pk=self.pk).count() >= 100:
            raise ValidationError('Максимум 100 фотографий в альбоме')


class AlbumPage(models.Model):
    """Страница альбома"""
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()
    template = models.ForeignKey(
        AlbumTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pages'
    )

    # Мини-превью страницы (можно использовать как фон)
    thumbnail = models.ImageField(upload_to='album_pages/thumbnails/', null=True, blank=True)

    class Meta:
        unique_together = ('album', 'page_number')
        ordering = ['album', 'page_number']
        verbose_name = 'Страница альбома'
        verbose_name_plural = 'Страницы альбомов'

    def __str__(self):
        return f"{self.album.title} - Page {self.page_number}"



class PhotoEdit(models.Model):
    """Редактирование фотографии"""
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='edits')
    filters_applied = models.JSONField(default=dict)
    crop_data = models.JSONField(default=dict)
    brightness = models.IntegerField(default=0, validators=[MinValueValidator(-100), MaxValueValidator(100)])
    contrast = models.IntegerField(default=0, validators=[MinValueValidator(-100), MaxValueValidator(100)])
    saturation = models.IntegerField(default=0, validators=[MinValueValidator(-100), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Редактирование фото'
        verbose_name_plural = 'Редактирования фото'
    
    def __str__(self):
        return f"Edit for {self.photo.title or self.photo.image.name}"
    
    def clean(self):
        # Валидация: значения фильтров в допустимых пределах
        for field in ['brightness', 'contrast', 'saturation']:
            value = getattr(self, field)
            if not (-100 <= value <= 100):
                raise ValidationError(f'{field} должен быть от -100 до 100')