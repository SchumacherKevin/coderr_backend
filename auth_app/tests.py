"""Tests for the auth_app API endpoints and commands."""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profile_app.models import UserProfile

GUESTS = [
    ('andrey', 'asdasd', 'customer'),
    ('kevin', 'asdasd24', 'business'),
]


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

    def test_weak_passwords(self):
        """Passwords rejected by Django's validators return 400."""
        weak = ['Ab1!', '12345678901', 'password', 'max12345']
        for password in weak:
            with self.subTest(password=password):
                self.payload['password'] = password
                self.payload['repeated_password'] = password
                response = self.assert_bad_request()
                self.assertIn('password', response.data)

    def assert_bad_request(self):
        """Post the payload and expect 400 without creating a profile."""
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserProfile.objects.exists())
        return response


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


class GuestUserCommandTests(APITestCase):
    """Tests for the create_guest_users management command."""

    def run_command(self):
        """Run the command without printing to the console."""
        call_command('create_guest_users', stdout=StringIO())

    def test_creates_both_guest_users(self):
        """The command creates both guests with profile, password and token."""
        self.run_command()
        for username, password, profile_type in GUESTS:
            user = User.objects.get(username=username)
            self.assertTrue(user.check_password(password))
            self.assertEqual(user.profile.type, profile_type)
            self.assertTrue(Token.objects.filter(user=user).exists())

    def test_command_is_idempotent(self):
        """Running the command twice does not create duplicates."""
        self.run_command()
        self.run_command()
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(UserProfile.objects.count(), 2)

    def test_resets_changed_password(self):
        """An existing guest gets the expected password back."""
        User.objects.create_user(username='andrey', password='changed')
        self.run_command()
        user = User.objects.get(username='andrey')
        self.assertTrue(user.check_password('asdasd'))
        self.assertEqual(user.profile.type, 'customer')

    def test_guest_can_log_in(self):
        """The frontend guest credentials work on the login endpoint."""
        self.run_command()
        for username, password, _ in GUESTS:
            payload = {'username': username, 'password': password}
            response = self.client.post(
                reverse('login'), payload, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
