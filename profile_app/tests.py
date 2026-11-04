"""Tests for the profile_app API endpoints."""
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from profile_app.models import UserProfile

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

PROFILE_FIELDS = {
    'user', 'username', 'first_name', 'last_name', 'file', 'location',
    'tel', 'description', 'working_hours', 'type', 'email', 'created_at',
}
STRING_FIELDS = [
    'first_name', 'last_name', 'location', 'tel', 'description',
    'working_hours',
]


def create_user_with_profile(username, profile_type='customer'):
    """Create a user together with its profile."""
    user = User.objects.create_user(
        username=username, email=f'{username}@mail.de', password='Secret123!'
    )
    UserProfile.objects.create(user=user, type=profile_type)
    return user


def create_test_image():
    """Return a tiny PNG file that can be uploaded."""
    buffer = BytesIO()
    Image.new('RGB', (1, 1)).save(buffer, format='PNG')
    return SimpleUploadedFile(
        'avatar.png', buffer.getvalue(), content_type='image/png'
    )


class ProfileTestBase(APITestCase):
    """Shared setup: a business owner and a second customer user."""

    def setUp(self):
        """Create two users and log in as the owner."""
        self.owner = create_user_with_profile('max', 'business')
        self.other = create_user_with_profile('anna', 'customer')
        self.url = self.profile_url(self.owner.pk)
        self.client.force_authenticate(user=self.owner)

    def profile_url(self, user_id):
        """Return the detail URL for the profile of the given user."""
        return reverse('profile-detail', kwargs={'pk': user_id})


class ProfileRetrieveTests(ProfileTestBase):
    """Tests for GET /api/profile/{pk}/."""

    def test_get_own_profile(self):
        """The owner gets the profile with exactly the documented fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), PROFILE_FIELDS)
        self.assertEqual(response.data['user'], self.owner.pk)
        self.assertEqual(response.data['username'], 'max')
        self.assertEqual(response.data['type'], 'business')

    def test_get_other_profile(self):
        """Every logged-in user may read any profile."""
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_empty_fields_are_strings(self):
        """Empty text fields are returned as '' and never as null."""
        response = self.client.get(self.url)
        for field in STRING_FIELDS:
            self.assertEqual(response.data[field], '', field)

    def test_get_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_unknown_user(self):
        """An unknown user ID returns 404."""
        response = self.client.get(self.profile_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProfileUpdateTests(ProfileTestBase):
    """Tests for PATCH /api/profile/{pk}/."""

    @classmethod
    def tearDownClass(cls):
        """Remove the uploaded test images."""
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_patch_own_profile(self):
        """The owner updates profile fields and user fields."""
        payload = {'first_name': 'Max', 'location': 'Berlin',
                   'email': 'new@mail.de'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location'], 'Berlin')
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.first_name, 'Max')
        self.assertEqual(self.owner.email, 'new@mail.de')
        self.assertEqual(self.owner.profile.location, 'Berlin')

    def test_patch_read_only_fields_are_ignored(self):
        """Username and type cannot be changed via PATCH."""
        payload = {'username': 'hacker', 'type': 'customer'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.username, 'max')
        self.assertEqual(self.owner.profile.type, 'business')

    def test_patch_upload_image(self):
        """A profile picture can be uploaded as multipart form data."""
        payload = {'file': create_test_image()}
        response = self.client.patch(self.url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile_pictures/avatar', response.data['file'])

    def test_patch_duplicate_email(self):
        """An email that belongs to another user returns 400."""
        payload = {'email': 'anna@mail.de'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_other_profile(self):
        """Editing someone else's profile returns 403."""
        url = self.profile_url(self.other.pk)
        response = self.client.patch(url, {'tel': '123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.patch(self.url, {'tel': '1'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_not_allowed(self):
        """Only PATCH is offered for updates, PUT returns 405."""
        response = self.client.put(self.url, {'tel': '1'}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_unknown_user(self):
        """An unknown user ID returns 404."""
        url = self.profile_url(9999)
        response = self.client.patch(url, {'tel': '1'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
