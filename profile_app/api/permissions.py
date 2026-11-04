"""Custom permissions for the profile_app API."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """Allow reading for everyone, writing only for the profile owner."""

    def has_object_permission(self, request, view, obj):
        """Grant safe methods to all, others only to obj.user."""
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user
