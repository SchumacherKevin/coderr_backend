"""Views for the reviews_app API."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListCreateAPIView

from reviews_app.models import Review

from .filters import ReviewFilter
from .permissions import IsCustomerForCreate
from .serializers import ReviewSerializer


class ReviewListView(ListCreateAPIView):
    """List reviews with filters; customers write new reviews."""

    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomerForCreate]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReviewFilter
    ordering_fields = ['updated_at', 'rating']

    def perform_create(self, serializer):
        """The logged-in customer becomes the reviewer."""
        serializer.save(reviewer=self.request.user)
