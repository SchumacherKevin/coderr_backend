"""Custom permissions for the offers_app API."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_business_user(user):
    """Return True if the user is logged in and has a business profile."""
    profile = getattr(user, 'profile', None)
    return bool(user.is_authenticated and profile
                and profile.type == 'business')


class IsBusinessUserOrReadOnly(BasePermission):
    """Allow reading for everyone, creating only for business users."""

    def has_permission(self, request, view):
        """Grant safe methods to all, others only to business users."""
        if request.method in SAFE_METHODS:
            return True
        return is_business_user(request.user)
