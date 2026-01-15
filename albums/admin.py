from django.contrib import admin
from import_export.admin import ExportMixin
from .models import Album, Photo, AlbumTemplate, AlbumPage, PhotoEdit
from .resources import AlbumResource

@admin.register(Album)
class AlbumAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = AlbumResource
    list_display = ('title', 'user', 'is_public', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'user__username')

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'uploaded_at', 'file_size')
    list_filter = ('uploaded_at', 'album')

@admin.register(AlbumTemplate)
class AlbumTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'is_premium')
    list_filter = ('is_premium', 'template_type')

@admin.register(AlbumPage)
class AlbumPageAdmin(admin.ModelAdmin):
    list_display = ('album', 'page_number', 'layout')

@admin.register(PhotoEdit)
class PhotoEditAdmin(admin.ModelAdmin):
    list_display = ('photo', 'brightness', 'contrast', 'saturation')
