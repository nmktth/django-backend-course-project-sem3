from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlbumViewSet, PhotoViewSet, BugReportViewSet

router = DefaultRouter()
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'photos', PhotoViewSet, basename='photo')
router.register(r'bug-reports', BugReportViewSet, basename='bugreport')

urlpatterns = [
    path('', include(router.urls)),
]
