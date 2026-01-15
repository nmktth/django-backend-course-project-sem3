from rest_framework import serializers
from .models import Album, Photo


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ('id', 'album', 'photo', 'description', 'created_at')
        read_only_fields = ('id', 'created_at')


class AlbumSerializer(serializers.ModelSerializer):
    photos_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Album
        fields = ('id', 'title', 'description', 'created_at', 'photos_count')
        read_only_fields = ('id', 'created_at')
    
    def get_photos_count(self, obj):
        return obj.photo_set.count()
