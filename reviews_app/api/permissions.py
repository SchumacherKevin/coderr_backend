"""Custom permissions for the reviews_app API."""
from rest_framework.permissions import BasePermission


class IsReviewer(BasePermission):
    """Only the author of a review may change or delete it."""

    def has_object_permission(self, request, view, obj):
        """Grant access if the user wrote this review."""
        return obj.reviewer == request.user
