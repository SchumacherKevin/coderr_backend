"""Permissions shared by several apps."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from profile_app.models import UserProfile


def has_profile_type(user, profile_type):
    """Return True if the user is logged in and has this profile type."""
    profile = getattr(user, 'profile', None)
    return bool(user.is_authenticated and profile
                and profile.type == profile_type)


class IsOwnerOrReadOnly(BasePermission):
    """Allow reading for everyone, writing only for the owner (obj.user)."""

    def has_object_permission(self, request, view, obj):
        """Grant safe methods to all, others only to obj.user."""
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user


class IsCustomerForCreate(BasePermission):
    """Logged-in users may read, only customers may create."""

    def has_permission(self, request, view):
        """Grant safe methods to logged-in users, POST only to customers."""
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return has_profile_type(
            request.user, UserProfile.ProfileType.CUSTOMER)
