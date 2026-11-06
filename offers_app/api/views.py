"""Views for the offers_app API."""
from django.db.models import Min
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated

from offers_app.models import Offer, OfferDetail
from profile_app.api.permissions import IsOwnerOrReadOnly

from .filters import OfferFilter
from .pagination import OfferPagination
from .permissions import IsBusinessUserOrReadOnly
from .serializers import (
    OfferDetailSerializer,
    OfferListSerializer,
    OfferRetrieveSerializer,
    OfferWriteSerializer,
)


def get_offer_queryset():
    """Return offers with user, details and their minimum price and time."""
    return Offer.objects.select_related('user').prefetch_related(
        'details').annotate(
            min_price=Min('details__price'),
            min_delivery_time=Min('details__delivery_time_in_days'))


class OfferListView(ListCreateAPIView):
    """Public offer list with filters; business users create offers."""

    permission_classes = [IsBusinessUserOrReadOnly]
    pagination_class = OfferPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ['title', 'description']
    ordering_fields = ['updated_at', 'min_price']
    ordering = ['-updated_at']

    def get_queryset(self):
        """Return all offers with their calculated minimum values."""
        return get_offer_queryset()

    def get_serializer_class(self):
        """Use the nested write serializer for POST."""
        if self.request.method == 'POST':
            return OfferWriteSerializer
        return OfferListSerializer

    def perform_create(self, serializer):
        """The logged-in business user becomes the creator."""
        serializer.save(user=self.request.user)


class OfferSingleView(RetrieveUpdateDestroyAPIView):
    """Read an offer; only its creator may update or delete it."""

    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """Return all offers with their calculated minimum values."""
        return get_offer_queryset()

    def get_serializer_class(self):
        """Use the nested write serializer for PATCH."""
        if self.request.method == 'PATCH':
            return OfferWriteSerializer
        return OfferRetrieveSerializer


class OfferDetailView(RetrieveAPIView):
    """Read a single package of an offer."""

    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailSerializer
    permission_classes = [IsAuthenticated]
