"""Custom permissions for the offers_app API."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from profile_app.api.permissions import has_profile_type
from profile_app.models import UserProfile


class IsBusinessUserOrReadOnly(BasePermission):
    """Allow reading for everyone, creating only for business users."""

    def has_permission(self, request, view):
        """Grant safe methods to all, others only to business users."""
        if request.method in SAFE_METHODS:
            return True
        return has_profile_type(
            request.user, UserProfile.ProfileType.BUSINESS)
