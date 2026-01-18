from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils import timezone

class AlbumTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('wedding', 'Свадьба'),
        ('travel', 'Путешествие'),
        ('portrait', 'Портрет'),
        ('family', 'Семья'),
        ('event', 'Событие'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    thumbnail = models.ImageField(upload_to='templates/', null=True, blank=True)
    css_styles = models.TextField(default='')
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Album(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_photo = models.ForeignKey('Photo', on_delete=models.SET_NULL, null=True, blank=True, related_name='album_cover')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    layout_template = models.ForeignKey(AlbumTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    views_count = models.IntegerField(default=0)
        
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'title')
    
    def __str__(self):
        return f"{self.title} by {self.user.username}"

class Photo(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(
        upload_to='photos/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField()  # в байтах
    dimensions = models.CharField(max_length=20, default='0x0')  # ширина x высота
    order_index = models.IntegerField(default=0)

    class Meta:
        ordering = ['order_index']
    
    def __str__(self):
        return self.title


class AlbumPage(models.Model):
    LAYOUT_CHOICES = [
        ('single', 'Одна фотография'),
        ('two_col', 'Два столбца'),
        ('three_col', 'Три столбца'),
        ('grid', 'Сетка 2x2'),
    ]
    
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()
    layout = models.CharField(max_length=50, choices=LAYOUT_CHOICES, default='two_col')
    background_color = models.CharField(max_length=7, default='#ffffff')
    title = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['page_number']
        unique_together = ('album', 'page_number')
    
    def __str__(self):
        return f"{self.album.title} - Page {self.page_number}"


class PhotoEdit(models.Model):
    photo = models.OneToOneField(Photo, on_delete=models.CASCADE, related_name='edit')
    filters_applied = models.JSONField(default=dict)
    crop_data = models.JSONField(default=dict)  # {"x": 0, "y": 0, "width": 100, "height": 100}
    brightness = models.IntegerField(default=0, validators=[MinValueValidator(-100), MaxValueValidator(100)])
    contrast = models.IntegerField(default=0, validators=[MinValueValidator(-100), MaxValueValidator(100)])
    saturation = models.IntegerField(default=0, validators=[MinValueValidator(-100), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Edit of {self.photo.title}"