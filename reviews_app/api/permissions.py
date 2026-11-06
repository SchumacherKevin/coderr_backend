"""Custom permissions for the reviews_app API."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from profile_app.api.permissions import has_profile_type
from profile_app.models import UserProfile


class IsCustomerForCreate(BasePermission):
    """Logged-in users may read, only customers may write reviews."""

    def has_permission(self, request, view):
        """Grant safe methods to logged-in users, POST only to customers."""
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return has_profile_type(
            request.user, UserProfile.ProfileType.CUSTOMER)
