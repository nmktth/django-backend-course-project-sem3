from django.contrib import admin
from .models import Album, Photo, AlbumTemplate, AlbumPage, PhotoEdit

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'is_public']
    list_filter = ['is_public', 'created_at']
    search_fields = ['title', 'description']
    inlines = []

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['title', 'album', 'uploaded_at']
    list_filter = ['album']
    search_fields = ['title']

@admin.register(AlbumTemplate)
class AlbumTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_premium']
    list_filter = ['is_premium']
    search_fields = ['name']

@admin.register(AlbumPage)
class AlbumPageAdmin(admin.ModelAdmin):
    list_display = ['album', 'page_number']
    list_filter = ['album']

@admin.register(PhotoEdit)
class PhotoEditAdmin(admin.ModelAdmin):
    list_display = ['photo', 'created_at']
    list_filter = ['created_at']
