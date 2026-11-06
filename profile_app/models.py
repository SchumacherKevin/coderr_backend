"""Models of profile_app."""
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Extends the Django user with Coderr-specific profile data."""

    class ProfileType(models.TextChoices):
        """The two kinds of users on Coderr."""

        CUSTOMER = 'customer', 'Customer'
        BUSINESS = 'business', 'Business'

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    type = models.CharField(max_length=10, choices=ProfileType.choices)
    file = models.ImageField(
        upload_to='profile_pictures/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, default='')
    tel = models.CharField(max_length=30, blank=True, default='')
    description = models.TextField(blank=True, default='')
    working_hours = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User profile'
        verbose_name_plural = 'User profiles'

    def __str__(self):
        """String representation of the user profile."""
        return f'{self.user.username} ({self.type})'
