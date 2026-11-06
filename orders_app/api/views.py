"""Views for the orders_app API."""
from django.db.models import Q
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from orders_app.models import Order

from .permissions import IsCustomerForCreate, IsOrderBusinessUser
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
)


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


class OrderSingleView(UpdateAPIView, DestroyAPIView):
    """Business user changes the status, staff deletes orders."""

    queryset = Order.objects.all()
    serializer_class = OrderStatusSerializer
    http_method_names = ['patch', 'delete', 'options']

    def get_permissions(self):
        """DELETE only for staff, PATCH only for the order's business user."""
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated(), IsOrderBusinessUser()]
