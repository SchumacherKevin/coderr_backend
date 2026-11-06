"""Views for the orders_app API."""
from django.db.models import Q
from rest_framework.generics import ListCreateAPIView

from orders_app.models import Order

from .permissions import IsCustomerForCreate
from .serializers import OrderCreateSerializer, OrderSerializer


class OrderListView(ListCreateAPIView):
    """List the user's orders; customers create new orders."""

    permission_classes = [IsCustomerForCreate]

    def get_queryset(self):
        """Return orders where the user is customer or business user."""
        user = self.request.user
        return Order.objects.filter(
            Q(customer_user=user) | Q(business_user=user))

    def get_serializer_class(self):
        """Use the create serializer for POST."""
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer
