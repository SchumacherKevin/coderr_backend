"""Management command that creates the guest accounts for the frontend."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
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
        """Create every guest user and report it on the console."""
        for guest in GUEST_USERS:
            self.create_guest(**guest)
            message = f"Guest user '{guest['username']}' is ready."
            self.stdout.write(self.style.SUCCESS(message))

    @transaction.atomic
    def create_guest(self, username, password, profile_type):
        """Create or update one guest with password, profile and token."""
        user, _ = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.save()
        UserProfile.objects.update_or_create(
            user=user, defaults={'type': profile_type}
        )
        Token.objects.get_or_create(user=user)
