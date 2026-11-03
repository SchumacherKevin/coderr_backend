"""Management command that creates the guest accounts for the frontend."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from profile_app.models import UserProfile

GUEST_USERS = [
    {'username': 'andrey', 'password': 'asdasd', 'profile_type': 'customer'},
    {'username': 'kevin', 'password': 'asdasd24', 'profile_type': 'business'},
]


class Command(BaseCommand):
    """Create or reset the guest users used by the frontend guest login."""

    help = 'Create or reset the customer and business guest accounts.'

    def handle(self, *args, **options):
        """Create every guest with password, profile and token."""
        for guest in GUEST_USERS:
            user, _ = User.objects.get_or_create(username=guest['username'])
            user.set_password(guest['password'])
            user.save()
            UserProfile.objects.update_or_create(
                user=user, defaults={'type': guest['profile_type']}
            )
            Token.objects.get_or_create(user=user)
            self.stdout.write(f"Guest user '{user.username}' is ready.")
