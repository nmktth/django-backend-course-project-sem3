"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from .views import IndexView, health_check
from albums.forms import StyledAuthenticationForm
from albums.views import (
    UserRegistrationView,
    UserLogoutView,
    UserProfileView,
    ChangePasswordView,
    register_view,
    DashboardView,
    create_album_view,
    edit_profile_view,
    profile_view,
    album_detail_view,
    toggle_public_view,
    add_photos_view,
    add_collaborator_view,
    remove_collaborator_view,
    delete_album_view,
    generate_collage_view,
    share_photo_view,
    public_photo_view,
)

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("", IndexView.as_view(), name="home"),
    path(
        "security-policy/",
        TemplateView.as_view(template_name="pages/security_policy.html"),
        name="security_policy",
    ),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/create/", create_album_view, name="create_album"),
    path("dashboard/album/<uuid:pk>/", album_detail_view, name="album_detail"),
    path("dashboard/album/<uuid:pk>/collage/", generate_collage_view, name="generate_collage"),
    path("dashboard/album/<uuid:pk>/toggle-public/", toggle_public_view, name="toggle_public"),
    path("dashboard/album/<uuid:pk>/add-photos/", add_photos_view, name="add_photos"),
    path(
        "dashboard/album/<uuid:pk>/add-collaborator/",
        add_collaborator_view,
        name="add_collaborator",
    ),
    path(
        "dashboard/album/<uuid:pk>/remove-collaborator/<int:user_id>/",
        remove_collaborator_view,
        name="remove_collaborator",
    ),
    path("dashboard/album/<uuid:pk>/delete/", delete_album_view, name="delete_album"),
    # Photo Sharing
    path("dashboard/photo/<int:pk>/share/", share_photo_view, name="share_photo"),
    path("s/photo/<uuid:token>/", public_photo_view, name="public_photo"),
    path("accounts/profile/", profile_view, name="profile"),
    path("accounts/profile/edit/", edit_profile_view, name="edit_profile"),
    path("admin/", admin.site.urls),
    # Web Auth
    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="auth/login.html", authentication_form=StyledAuthenticationForm
        ),
        name="login",
    ),
    path("accounts/logout/", LogoutView.as_view(next_page="home"), name="web_logout"),
    path("accounts/register/", register_view, name="register"),
    # Swagger UI & Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include("albums.urls")),
    # Auth endpoints
    path("api/auth/register/", UserRegistrationView.as_view(), name="api_register"),
    path("api/auth/login/", obtain_auth_token, name="api_login"),
    path("api/auth/logout/", UserLogoutView.as_view(), name="api_logout"),
    path("api/auth/profile/", UserProfileView.as_view(), name="api_profile"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="api_change_password"),
]
