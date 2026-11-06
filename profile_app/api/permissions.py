"""Custom permissions for the profile_app API."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """Allow reading for everyone, writing only for the profile owner."""

    def has_object_permission(self, request, view, obj):
        """Grant safe methods to all, others only to obj.user."""
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user


def has_profile_type(user, profile_type):
    """Return True if the user is logged in and has this profile type."""
    profile = getattr(user, 'profile', None)
    return bool(user.is_authenticated and profile
                and profile.type == profile_type)
