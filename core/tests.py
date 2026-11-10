"""Tests for the shared permissions in core.permissions."""
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from core.permissions import (
    IsCustomerForCreate,
    IsOwnerOrReadOnly,
    has_profile_type,
)
from profile_app.models import UserProfile


def create_user(username, profile_type=None):
    """Create a user, with a profile if a type is given."""
    user = User.objects.create_user(username=username, password='x')
    if profile_type:
        UserProfile.objects.create(user=user, type=profile_type)
    return user


def fake_request(user, method):
    """Return the parts of a request the permissions look at."""
    return SimpleNamespace(user=user, method=method)


class HasProfileTypeTests(TestCase):
    """Tests for has_profile_type()."""

    def test_matching_type(self):
        """A user with this profile type returns True."""
        self.assertTrue(has_profile_type(
            create_user('max', 'business'), 'business'))

    def test_other_type(self):
        """A user with another profile type returns False."""
        self.assertFalse(has_profile_type(
            create_user('anna', 'customer'), 'business'))

    def test_without_profile_or_login(self):
        """Users without profile and anonymous users return False."""
        self.assertFalse(has_profile_type(create_user('admin'), 'customer'))
        self.assertFalse(has_profile_type(AnonymousUser(), 'customer'))


class IsOwnerOrReadOnlyTests(TestCase):
    """Tests for IsOwnerOrReadOnly."""

    def setUp(self):
        """Create an owner, another user and an object of the owner."""
        self.owner = create_user('max')
        self.other = create_user('lisa')
        self.obj = SimpleNamespace(user=self.owner)

    def allowed(self, user, method):
        """Ask the permission for the object."""
        request = fake_request(user, method)
        return IsOwnerOrReadOnly().has_object_permission(
            request, None, self.obj)

    def test_everyone_may_read(self):
        """GET is allowed for every user."""
        self.assertTrue(self.allowed(self.other, 'GET'))

    def test_only_owner_may_write(self):
        """PATCH and DELETE are only allowed for the owner."""
        self.assertTrue(self.allowed(self.owner, 'PATCH'))
        self.assertFalse(self.allowed(self.other, 'PATCH'))
        self.assertFalse(self.allowed(self.other, 'DELETE'))


class IsCustomerForCreateTests(TestCase):
    """Tests for IsCustomerForCreate."""

    def allowed(self, user, method):
        """Ask the permission for the request."""
        return IsCustomerForCreate().has_permission(
            fake_request(user, method), None)

    def test_logged_in_users_may_read(self):
        """GET needs a login, but no special profile type."""
        self.assertTrue(self.allowed(create_user('max', 'business'), 'GET'))
        self.assertFalse(self.allowed(AnonymousUser(), 'GET'))

    def test_only_customers_may_create(self):
        """POST is only allowed for customers."""
        self.assertTrue(self.allowed(create_user('anna', 'customer'), 'POST'))
        self.assertFalse(self.allowed(create_user('max', 'business'), 'POST'))
