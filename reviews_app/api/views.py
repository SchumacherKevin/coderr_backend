"""Views for the reviews_app API."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsCustomerForCreate
from reviews_app.models import Review

from .filters import ReviewFilter
from .permissions import IsReviewer
from .serializers import ReviewSerializer, ReviewUpdateSerializer


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


class ReviewSingleView(UpdateAPIView, DestroyAPIView):
    """Only the reviewer may update or delete a review."""

    queryset = Review.objects.all()
    serializer_class = ReviewUpdateSerializer
    permission_classes = [IsAuthenticated, IsReviewer]
    http_method_names = ['patch', 'delete', 'options']
