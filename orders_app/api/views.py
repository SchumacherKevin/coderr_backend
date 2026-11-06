"""Views for the orders_app API."""
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders_app.models import Order
from profile_app.api.permissions import IsCustomerForCreate
from profile_app.models import UserProfile

from .permissions import IsOrderBusinessUser
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


class OrderCountView(APIView):
    """Count the orders of a business user with the status of this view."""

    permission_classes = [IsAuthenticated]
    order_status = Order.Status.IN_PROGRESS
    response_key = 'order_count'

    def get(self, request, business_user_id):
        """Return the number of orders, 404 if there is no business user."""
        business_user = get_object_or_404(
            User, pk=business_user_id,
            profile__type=UserProfile.ProfileType.BUSINESS)
        count = Order.objects.filter(
            business_user=business_user, status=self.order_status).count()
        return Response({self.response_key: count})


class CompletedOrderCountView(OrderCountView):
    """Count the completed orders of a business user."""

    order_status = Order.Status.COMPLETED
    response_key = 'completed_order_count'
