from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlbumViewSet, PhotoViewSet, AlbumTemplateViewSet, AlbumPageViewSet, PhotoEditViewSet
from .views_auth import RegisterView, LoginView, MeView, RefreshTokenView

router = DefaultRouter()
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'photos', PhotoViewSet, basename='photo')
router.register(r'templates', AlbumTemplateViewSet, basename='template')
router.register(r'pages', AlbumPageViewSet, basename='page')
router.register(r'edits', PhotoEditViewSet, basename='edit')

urlpatterns = [
    # Auth endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    
    # API routes
    path('', include(router.urls)),
]
