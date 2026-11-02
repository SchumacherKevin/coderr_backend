from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profile_app.models import UserProfile


class RegistrationTests(APITestCase):
    """Tests for POST /api/registration/."""

    def setUp(self):
        """Prepare the URL and a valid payload."""
        self.url = reverse('registration')
        self.payload = {
            'username': 'max',
            'email': 'max@mail.de',
            'password': 'Secret123!',
            'repeated_password': 'Secret123!',
            'type': 'customer',
        }

    def test_registration_success(self):
        """Valid data creates user, profile and token and returns 201."""
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='max')
        self.assertEqual(response.data['token'],
                         Token.objects.get(user=user).key)
        self.assertEqual(response.data['user_id'], user.id)
        self.assertEqual(set(response.data), {
                         'token', 'username', 'email', 'user_id'})
        self.assertEqual(user.profile.type, 'customer')
        self.assertTrue(user.check_password('Secret123!'))

    def test_passwords_do_not_match(self):
        """Different passwords return 400."""
        self.payload['repeated_password'] = 'Other123!'
        self.assert_bad_request()

    def test_missing_field(self):
        """A missing required field returns 400."""
        del self.payload['email']
        self.assert_bad_request()

    def test_invalid_type(self):
        """An unknown profile type returns 400."""
        self.payload['type'] = 'admin'
        self.assert_bad_request()

    def test_duplicate_username(self):
        """An existing username returns 400."""
        User.objects.create_user(username='max', email='other@mail.de')
        self.assert_bad_request()

    def test_duplicate_email(self):
        """An existing email returns 400."""
        User.objects.create_user(username='other', email='max@mail.de')
        self.assert_bad_request()

    def assert_bad_request(self):
        """Post the payload and expect 400 without creating a profile."""
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserProfile.objects.exists())
