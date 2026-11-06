"""Tests for the orders_app models and API endpoints."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.testing import AdminQueryCountMixin
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


def order_url(pk):
    """Return the URL of a single order."""
    return reverse('order-detail', kwargs={'pk': pk})


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


class OrderSingleTestBase(OrderTestBase):
    """Shared setup: one order between anna and max."""

    def setUp(self):
        """Create the order and log in as its business user."""
        super().setUp()
        self.order = create_order(self.customer, self.detail)
        self.url = order_url(self.order.pk)
        self.client.force_authenticate(user=self.business)


class OrderUpdateTests(OrderSingleTestBase):
    """Tests for PATCH /api/orders/{id}/."""

    def patch(self, data, url=None):
        """Send the changes as JSON."""
        return self.client.patch(url or self.url, data, format='json')

    def test_business_user_updates_status(self):
        """The business user of the order changes the status."""
        response = self.patch({'status': 'completed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), ORDER_FIELDS)
        self.assertEqual(response.data['status'], 'completed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')

    def test_patch_invalid_status(self):
        """Unknown status values return 400."""
        response = self.patch({'status': 'done'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_without_status(self):
        """A PATCH without status returns 400."""
        response = self.patch({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_other_fields(self):
        """Fields other than status are not allowed."""
        response = self.patch({'status': 'completed', 'price': 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'in_progress')

    def test_patch_as_customer(self):
        """The customer of the order may not change the status."""
        self.client.force_authenticate(user=self.customer)
        response = self.patch({'status': 'cancelled'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_as_other_business_user(self):
        """Business users of other orders may not change the status."""
        self.client.force_authenticate(user=create_user('lisa'))
        response = self.patch({'status': 'completed'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.patch({'status': 'completed'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_unknown_order(self):
        """An unknown ID returns 404."""
        response = self.patch({'status': 'completed'}, order_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OrderDeleteTests(OrderSingleTestBase):
    """Tests for DELETE /api/orders/{id}/."""

    def setUp(self):
        """Additionally create a staff user."""
        super().setUp()
        self.admin = User.objects.create_user(
            username='admin', password='Secret123!', is_staff=True)

    def test_staff_deletes_order(self):
        """Staff users delete orders."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Order.objects.count(), 0)

    def test_delete_as_business_user(self):
        """Even the business user of the order may not delete it."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Order.objects.count(), 1)

    def test_delete_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_unknown_order(self):
        """An unknown ID returns 404."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(order_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OrderCountTests(OrderTestBase):
    """Tests for GET /api/order-count/ and /api/completed-order-count/."""

    def setUp(self):
        """Create orders of max with different status."""
        super().setUp()
        create_order(self.customer, self.detail)
        create_order(self.customer, self.detail)
        create_order(self.customer, self.detail, status='completed')
        create_order(self.customer, self.detail, status='cancelled')
        other_detail = create_offer(create_user('lisa')).details.first()
        create_order(self.customer, other_detail)

    def get_count(self, name, user_id):
        """Request one of the count endpoints."""
        url = reverse(name, kwargs={'business_user_id': user_id})
        return self.client.get(url)

    def test_order_count(self):
        """Counts the orders of the business user that are in progress."""
        response = self.get_count('order-count', self.business.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'order_count': 2})

    def test_completed_order_count(self):
        """Counts the completed orders of the business user."""
        response = self.get_count('completed-order-count', self.business.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'completed_order_count': 1})

    def test_count_without_orders(self):
        """A business user without orders has a count of 0."""
        new_business = create_user('tom')
        response = self.get_count('order-count', new_business.pk)
        self.assertEqual(response.data, {'order_count': 0})

    def test_count_unknown_user(self):
        """An unknown user ID returns 404."""
        for name in ['order-count', 'completed-order-count']:
            response = self.get_count(name, 999)
            self.assertEqual(
                response.status_code, status.HTTP_404_NOT_FOUND, name)

    def test_count_for_customer_id(self):
        """The ID of a customer is not a business user, so 404."""
        response = self.get_count('order-count', self.customer.pk)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_count_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        for name in ['order-count', 'completed-order-count']:
            response = self.get_count(name, self.business.pk)
            self.assertEqual(
                response.status_code, status.HTTP_401_UNAUTHORIZED, name)


class OrderQueryCountTests(AdminQueryCountMixin, OrderTestBase):
    """Order list and order admin do not run one query per order."""

    def setUp(self):
        """Create one order of the customer anna."""
        super().setUp()
        create_order(self.customer, self.detail)

    def create_order(self):
        """Create another order of anna."""
        create_order(self.customer, self.detail)

    def test_order_list(self):
        """More orders do not add queries to the order list."""
        self.assert_queries_constant(self.list_url, self.create_order)

    def test_order_changelist(self):
        """More orders do not add queries to the admin order list."""
        self.login_as_admin()
        self.assert_queries_constant(
            reverse('admin:orders_app_order_changelist'), self.create_order)
