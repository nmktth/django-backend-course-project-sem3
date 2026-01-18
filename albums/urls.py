from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.conf import settings
from django.conf.urls.static import static


# Router для REST API
router = DefaultRouter()
router.register(r'albums', views.AlbumViewSet, basename='album')
router.register(r'photos', views.PhotoViewSet, basename='photo')
router.register(r'templates', views.AlbumTemplateViewSet, basename='template')
router.register(r'pages', views.AlbumPageViewSet, basename='page')
router.register(r'edits', views.PhotoEditViewSet, basename='edit')

app_name = 'albums'

urlpatterns = [
    path('api/albums/create-form/', views.create_album_form, name='create_album_form'),
    path('api/albums/create-quick/', views.create_quick_album, name='create_quick_album'),
    path('my-albums/', views.my_albums_html, name='my_albums_html'),
    path('albums/<int:album_id>/upload/', views.upload_photo, name='upload_photo'),
    path('albums/<int:album_id>/', views.album_detail, name='album_detail'),
    
    # Юзер
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile_views, name='profile'),
    path('account-details/', views.account_details, name='account_details'),
    path('edit-account-details/', views.edit_account_details, name='edit_account_details'),
    path('update-account-details/', views.update_account_details, name='update_account_details'),
    path('logout/', views.logout_view, name='logout'),

    # REST API routes (автоматически генерируются из router)
    path('api/', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)