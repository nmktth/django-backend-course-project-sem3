from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from albums.models import Album, Photo, BugReport
import uuid


class AlbumModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.album = Album.objects.create(
            user=self.user, title="Test Album", description="Test Description"
        )

    def test_album_creation(self):
        self.assertEqual(self.album.title, "Test Album")
        self.assertEqual(self.album.user.username, "testuser")
        self.assertIsInstance(self.album.id, uuid.UUID)
        self.assertFalse(self.album.is_public)

    def test_album_str(self):
        self.assertEqual(str(self.album), "Test Album (testuser)")


class PhotoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.album = Album.objects.create(user=self.user, title="Test Album")

    def test_photo_creation(self):
        # Create a dummy image
        image = SimpleUploadedFile(
            name="test_image.jpg", content=b"\x00\x00", content_type="image/jpeg"
        )
        photo = Photo.objects.create(album=self.album, image=image)
        self.assertEqual(photo.album, self.album)
        self.assertTrue(photo.image.name.endswith(".jpg"))


class UserProfileSignalTest(TestCase):
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username="profiletest", password="password123")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.user, user)


class BugReportModelTest(TestCase):
    def test_bug_report_creation(self):
        user = User.objects.create_user(username="buguser", password="password123")
        bug = BugReport.objects.create(
            user=user,
            title="Test Bug",
            description="Bug Description",
            status="open"
        )
        self.assertEqual(bug.title, "Test Bug")
        self.assertEqual(bug.status, "open")
        self.assertEqual(str(bug), "Bug: Test Bug (open)")


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.login_url = reverse("login")
        self.dashboard_url = reverse("dashboard")

    def test_dashboard_redirect_if_not_logged_in(self):
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.dashboard_url}")

    def test_dashboard_access_logged_in(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")


class CreateAlbumViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.create_album_url = reverse("create_album")

    def test_create_album_post(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            self.create_album_url, {"title": "New Album", "description": "Description"}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(Album.objects.filter(title="New Album", user=self.user).exists())


class AlbumAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.token_url = reverse("api_login")
        # Obtain auth token
        response = self.client.post(
            self.token_url, {"username": "testuser", "password": "password123"}
        )
        self.token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token)

        self.album = Album.objects.create(user=self.user, title="API Album")

    def test_get_albums_list(self):
        url = "/api/albums/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should contain 1 album
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "API Album")

    def test_create_album_api(self):
        url = "/api/albums/"
        data = {"title": "Created via API", "description": "API Desc"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Album.objects.count(), 2)

    def test_retrieve_album_detail(self):
        url = f"/api/albums/{self.album.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "API Album")

    def test_delete_album_api(self):
        url = f"/api/albums/{self.album.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Album.objects.count(), 0)
