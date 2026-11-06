"""URL routes for the orders_app API."""
from django.urls import path

from .views import OrderListView

urlpatterns = [
    path('orders/', OrderListView.as_view(), name='order-list'),
]
