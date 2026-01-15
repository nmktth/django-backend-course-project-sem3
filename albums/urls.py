from rest_framework.routers import DefaultRouter
from .views import AlbumViewSet, PhotoViewSet, AlbumTemplateViewSet

router = DefaultRouter()
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'photos', PhotoViewSet, basename='photo')
router.register(r'templates', AlbumTemplateViewSet, basename='template')

urlpatterns = router.urls
