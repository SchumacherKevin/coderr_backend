"""Tests for the offers_app models."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from offers_app.models import Offer, OfferDetail


def create_detail(offer, offer_type='basic', **fields):
    """Create one offer detail, values not passed get a default."""
    defaults = {
        'title': f'{offer_type} Design', 'revisions': 2,
        'delivery_time_in_days': 5, 'price': 100,
    }
    defaults.update(fields)
    return OfferDetail.objects.create(
        offer=offer, offer_type=offer_type, **defaults)


def create_offer(user, title='Website Design'):
    """Create an offer with the three detail types basic, standard, premium."""
    offer = Offer.objects.create(
        user=user, title=title, description='Professionelles Design')
    create_detail(offer, 'basic', features=['Logo Design'])
    create_detail(offer, 'standard', price=200, delivery_time_in_days=7)
    create_detail(offer, 'premium', price=500, delivery_time_in_days=10)
    return offer


class OfferModelTests(TestCase):
    """Tests for the Offer and OfferDetail models."""

    def setUp(self):
        """Create a business user with one complete offer."""
        self.user = User.objects.create_user(
            username='max', password='Secret123!')
        self.offer = create_offer(self.user)

    def test_offer_belongs_to_user(self):
        """The creator reaches his offers via user.offers."""
        self.assertEqual(list(self.user.offers.all()), [self.offer])

    def test_offer_optional_fields(self):
        """Image may be empty, timestamps are set automatically."""
        self.assertFalse(self.offer.image)
        self.assertIsNotNone(self.offer.created_at)
        self.assertIsNotNone(self.offer.updated_at)

    def test_offer_has_three_details(self):
        """The details of an offer are reachable via offer.details."""
        types = set(self.offer.details.values_list('offer_type', flat=True))
        self.assertEqual(types, {'basic', 'standard', 'premium'})

    def test_detail_stores_values(self):
        """Price is a decimal, features are stored as a list."""
        detail = self.offer.details.get(offer_type='basic')
        self.assertEqual(detail.price, Decimal('100.00'))
        self.assertEqual(detail.delivery_time_in_days, 5)
        self.assertEqual(detail.features, ['Logo Design'])

    def test_detail_features_default_to_empty_list(self):
        """Without features the field is an empty list, never null."""
        offer = Offer.objects.create(user=self.user, title='Logo')
        detail = create_detail(offer)
        self.assertEqual(detail.features, [])

    def test_unlimited_revisions_allowed(self):
        """The frontend sends -1 for unlimited revisions."""
        detail = self.offer.details.get(offer_type='premium')
        detail.revisions = -1
        detail.save()
        detail.refresh_from_db()
        self.assertEqual(detail.revisions, -1)

    def test_offer_type_unique_per_offer(self):
        """An offer cannot have two details with the same offer_type."""
        with self.assertRaises(IntegrityError):
            create_detail(self.offer, 'basic')

    def test_same_offer_type_in_different_offers(self):
        """Two different offers may both have a basic detail."""
        create_offer(self.user, title='Logo Design')
        self.assertEqual(
            OfferDetail.objects.filter(offer_type='basic').count(), 2)

    def test_delete_offer_deletes_details(self):
        """Deleting an offer also deletes its details."""
        self.offer.delete()
        self.assertEqual(OfferDetail.objects.count(), 0)

    def test_delete_user_deletes_offers(self):
        """Deleting the creator also deletes his offers."""
        self.user.delete()
        self.assertEqual(Offer.objects.count(), 0)

    def test_newest_offer_comes_first(self):
        """Offers are ordered by updated_at, newest first."""
        newer = create_offer(self.user, title='Logo Design')
        self.assertEqual(list(Offer.objects.all()), [newer, self.offer])

    def test_str(self):
        """Readable names for the admin."""
        detail = self.offer.details.get(offer_type='basic')
        self.assertEqual(str(self.offer), 'Website Design (max)')
        self.assertEqual(str(detail), 'Website Design - basic')
