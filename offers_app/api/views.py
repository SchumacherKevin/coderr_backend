"""Views for the offers_app API."""
from django.db.models import Min
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from offers_app.models import Offer

from .filters import OfferFilter
from .pagination import OfferPagination
from .serializers import OfferListSerializer


class OfferListView(ListAPIView):
    """Public, paginated list of offers with filters, search and ordering."""

    serializer_class = OfferListSerializer
    permission_classes = [AllowAny]
    pagination_class = OfferPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ['title', 'description']
    ordering_fields = ['updated_at', 'min_price']
    ordering = ['-updated_at']

    def get_queryset(self):
        """Return all offers with their calculated minimum values."""
        return Offer.objects.select_related('user').prefetch_related(
            'details').annotate(
                min_price=Min('details__price'),
                min_delivery_time=Min('details__delivery_time_in_days'))
