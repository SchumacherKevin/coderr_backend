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


class LoginTests(APITestCase):
    """Tests for POST /api/login/."""

    def setUp(self):
        """Create a user with token and prepare the URL and payload."""
        self.url = reverse('login')
        self.user = User.objects.create_user(
            username='max', email='max@mail.de', password='Secret123!'
        )
        self.token = Token.objects.create(user=self.user)
        self.payload = {'username': 'max', 'password': 'Secret123!'}

    def test_login_success(self):
        """Valid credentials return 200 with token and user data."""
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'token': self.token.key,
            'username': 'max',
            'email': 'max@mail.de',
            'user_id': self.user.pk,
        })

    def test_login_creates_missing_token(self):
        """A user without token gets a new one on login."""
        self.token.delete()
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_token = Token.objects.get(user=self.user)
        self.assertEqual(response.data['token'], new_token.key)

    def test_wrong_password(self):
        """A wrong password returns 400."""
        self.payload['password'] = 'Wrong123!'
        self.assert_bad_request()

    def test_unknown_user(self):
        """An unknown username returns 400."""
        self.payload['username'] = 'nobody'
        self.assert_bad_request()

    def test_missing_field(self):
        """A missing password returns 400."""
        del self.payload['password']
        self.assert_bad_request()

    def assert_bad_request(self):
        """Post the payload and expect 400 without a token in the response."""
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', response.data)
