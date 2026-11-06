"""Tests for the orders_app models and API endpoints."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from offers_app.tests import create_offer, create_user
from orders_app.models import Order

ORDER_FIELDS = {
    'id', 'customer_user', 'business_user', 'title', 'revisions',
    'delivery_time_in_days', 'price', 'features', 'offer_type', 'status',
    'created_at', 'updated_at',
}


def create_order(customer, offer_detail, **fields):
    """Create an order as a copy of the given offer detail."""
    return Order.objects.create(
        customer_user=customer,
        business_user=offer_detail.offer.user,
        title=offer_detail.title,
        revisions=offer_detail.revisions,
        delivery_time_in_days=offer_detail.delivery_time_in_days,
        price=offer_detail.price,
        features=offer_detail.features,
        offer_type=offer_detail.offer_type,
        **fields,
    )


class OrderModelTests(TestCase):
    """Tests for the Order model."""

    def setUp(self):
        """Create a business user with an offer and an order of a customer."""
        self.business = create_user('max')
        self.customer = create_user('anna', 'customer')
        self.detail = create_offer(self.business).details.get(
            offer_type='basic')
        self.order = create_order(self.customer, self.detail)

    def test_order_copies_offer_detail(self):
        """The order stores the package data at the time of ordering."""
        self.assertEqual(self.order.title, 'basic Design')
        self.assertEqual(self.order.price, Decimal('100.00'))
        self.assertEqual(self.order.features, ['Logo Design'])
        self.assertEqual(self.order.offer_type, 'basic')

    def test_default_status_is_in_progress(self):
        """A new order is in progress."""
        self.assertEqual(self.order.status, 'in_progress')

    def test_status_choices(self):
        """Only in_progress, completed and cancelled are valid."""
        self.assertEqual(
            Order.Status.values, ['in_progress', 'completed', 'cancelled'])
        self.order.status = 'unknown'
        with self.assertRaises(ValidationError):
            self.order.full_clean()

    def test_timestamps_are_set(self):
        """created_at and updated_at are set automatically."""
        self.assertIsNotNone(self.order.created_at)
        self.assertIsNotNone(self.order.updated_at)

    def test_related_names(self):
        """Customer and business user reach their orders."""
        self.assertEqual(list(self.customer.customer_orders.all()),
                         [self.order])
        self.assertEqual(list(self.business.business_orders.all()),
                         [self.order])

    def test_order_survives_offer_change(self):
        """Changing the offer later does not change the order."""
        self.detail.price = 999
        self.detail.save()
        self.order.refresh_from_db()
        self.assertEqual(self.order.price, Decimal('100.00'))

    def test_order_survives_offer_delete(self):
        """Deleting the offer keeps the order."""
        self.detail.offer.delete()
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())

    def test_delete_customer_deletes_orders(self):
        """Deleting the customer also deletes his orders."""
        self.customer.delete()
        self.assertEqual(Order.objects.count(), 0)

    def test_newest_order_comes_first(self):
        """Orders are ordered by created_at, newest first."""
        newer = create_order(self.customer, self.detail)
        Order.objects.filter(pk=self.order.pk).update(
            created_at=self.order.created_at.replace(year=2020))
        self.assertEqual(list(Order.objects.all()), [newer, self.order])

    def test_str(self):
        """Readable name for the admin."""
        self.assertEqual(
            str(self.order), f'Order {self.order.pk}: basic Design (anna)')

    def test_user_model_is_django_user(self):
        """Orders point to the Django user."""
        self.assertIsInstance(self.order.business_user, User)


class OrderTestBase(APITestCase):
    """Shared setup: an offer of max and a customer anna."""

    def setUp(self):
        """Create users and an offer, log in as the customer."""
        self.business = create_user('max')
        self.customer = create_user('anna', 'customer')
        self.detail = create_offer(self.business).details.get(
            offer_type='basic')
        self.list_url = reverse('order-list')
        self.client.force_authenticate(user=self.customer)


class OrderListTests(OrderTestBase):
    """Tests for GET /api/orders/."""

    def setUp(self):
        """Create an order of anna and an order between two other users."""
        super().setUp()
        self.order = create_order(self.customer, self.detail)
        other_detail = create_offer(create_user('lisa')).details.first()
        create_order(create_user('tom', 'customer'), other_detail)

    def get_ids(self):
        """Request the list and return the IDs of the orders."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [order['id'] for order in response.data]

    def test_customer_sees_own_orders(self):
        """The customer only sees orders he placed."""
        self.assertEqual(self.get_ids(), [self.order.pk])

    def test_business_user_sees_received_orders(self):
        """The business user only sees orders he received."""
        self.client.force_authenticate(user=self.business)
        self.assertEqual(self.get_ids(), [self.order.pk])

    def test_list_fields(self):
        """Each order has exactly the documented fields."""
        order = self.client.get(self.list_url).data[0]
        self.assertEqual(set(order), ORDER_FIELDS)
        self.assertEqual(order['customer_user'], self.customer.pk)
        self.assertEqual(order['business_user'], self.business.pk)
        self.assertEqual(order['price'], 100)

    def test_list_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderCreateTests(OrderTestBase):
    """Tests for POST /api/orders/."""

    def post(self, data):
        """Send the order data as JSON."""
        return self.client.post(self.list_url, data, format='json')

    def test_create_order(self):
        """A customer orders a package, the data is copied into the order."""
        response = self.post({'offer_detail_id': self.detail.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data), ORDER_FIELDS)
        order = Order.objects.get()
        self.assertEqual(order.customer_user, self.customer)
        self.assertEqual(order.business_user, self.business)
        self.assertEqual(order.title, self.detail.title)
        self.assertEqual(order.status, 'in_progress')

    def test_create_ignores_other_fields(self):
        """Customer, business user and status cannot be set by the client."""
        response = self.post({
            'offer_detail_id': self.detail.pk, 'status': 'completed',
            'customer_user': self.business.pk, 'price': 1})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['customer_user'], self.customer.pk)
        self.assertEqual(response.data['price'], 100)

    def test_create_without_offer_detail_id(self):
        """offer_detail_id is required."""
        response = self.post({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_invalid_offer_detail_id(self):
        """offer_detail_id must be a number."""
        response = self.post({'offer_detail_id': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_unknown_offer_detail(self):
        """An unknown offer detail returns 404."""
        response = self.post({'offer_detail_id': 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_as_business_user(self):
        """Only customers may place orders."""
        self.client.force_authenticate(user=self.business)
        response = self.post({'offer_detail_id': self.detail.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.post({'offer_detail_id': self.detail.pk})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
