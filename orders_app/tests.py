"""Tests for the orders_app models."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from offers_app.tests import create_offer, create_user
from orders_app.models import Order


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
