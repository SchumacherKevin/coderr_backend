"""Views for the profile_app API."""
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from profile_app.models import UserProfile

from .permissions import IsOwnerOrReadOnly
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


class BusinessProfileListView(ListAPIView):
    """List all business profiles."""

    queryset = UserProfile.objects.filter(
        type=UserProfile.ProfileType.BUSINESS).select_related('user')
    serializer_class = BusinessProfileListSerializer
    permission_classes = [IsAuthenticated]


class CustomerProfileListView(ListAPIView):
    """List all customer profiles."""

    queryset = UserProfile.objects.filter(
        type=UserProfile.ProfileType.CUSTOMER).select_related('user')
    serializer_class = CustomerProfileListSerializer
    permission_classes = [IsAuthenticated]
