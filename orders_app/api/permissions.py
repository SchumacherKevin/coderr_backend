"""Custom permissions for the orders_app API."""
from rest_framework.permissions import BasePermission


class IsOrderBusinessUser(BasePermission):
    """Only the business user of the order may change it."""

    def has_object_permission(self, request, view, obj):
        """Grant access if the user received this order."""
        return obj.business_user == request.user
