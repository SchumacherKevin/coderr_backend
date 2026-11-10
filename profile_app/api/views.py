"""Views for the profile_app API."""
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsOwnerOrReadOnly
from profile_app.models import UserProfile

from .serializers import (
    BusinessProfileListSerializer,
    CustomerProfileListSerializer,
    ProfileSerializer,
)


class ProfileDetailView(RetrieveUpdateAPIView):
    """Read any profile, update only your own. pk is the user ID."""

    queryset = UserProfile.objects.select_related('user')
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'user'
    lookup_url_kwarg = 'pk'
    http_method_names = ['get', 'patch', 'head', 'options']


class ProfileListView(ListAPIView):
    """Base view: list all profiles of the type set in profile_type."""

    permission_classes = [IsAuthenticated]
    profile_type = None

    def get_queryset(self):
        """Return only profiles of this view's type, with their user."""
        return UserProfile.objects.filter(
            type=self.profile_type).select_related('user')


class BusinessProfileListView(ProfileListView):
    """List all business profiles."""

    profile_type = UserProfile.ProfileType.BUSINESS
    serializer_class = BusinessProfileListSerializer


class CustomerProfileListView(ProfileListView):
    """List all customer profiles."""

    profile_type = UserProfile.ProfileType.CUSTOMER
    serializer_class = CustomerProfileListSerializer
