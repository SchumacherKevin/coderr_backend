"""Views for the profile_app API."""
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from profile_app.models import UserProfile

from .permissions import IsOwnerOrReadOnly
from .serializers import ProfileSerializer


class ProfileDetailView(RetrieveUpdateAPIView):
    """Read any profile, update only your own. pk is the user ID."""

    queryset = UserProfile.objects.select_related('user')
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'user'
    lookup_url_kwarg = 'pk'
    http_method_names = ['get', 'patch', 'head', 'options']