"""Tests for the offers_app models and API endpoints."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from offers_app.models import Offer, OfferDetail
from profile_app.models import UserProfile

LIST_FIELDS = {
    'id', 'user', 'title', 'image', 'description', 'created_at',
    'updated_at', 'details', 'min_price', 'min_delivery_time',
    'user_details',
}


def create_detail(offer, offer_type='basic', **fields):
    """Create one offer detail, values not passed get a default."""
    defaults = {
        'title': f'{offer_type} Design', 'revisions': 2,
        'delivery_time_in_days': 5, 'price': 100,
    }
    defaults.update(fields)
    return OfferDetail.objects.create(
        offer=offer, offer_type=offer_type, **defaults)


def create_user(username, profile_type='business'):
    """Create a user together with its profile."""
    user = User.objects.create_user(
        username=username, password='Secret123!',
        first_name=username.title(), last_name='Muster')
    UserProfile.objects.create(user=user, type=profile_type)
    return user


def create_offer(user, title='Website Design',
                 description='Professionelles Design'):
    """Create an offer with the three detail types basic, standard, premium."""
    offer = Offer.objects.create(
        user=user, title=title, description=description)
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


class OfferListTests(APITestCase):
    """Tests for GET /api/offers/."""

    def setUp(self):
        """Create two business users with offers of different prices."""
        self.url = reverse('offer-list')
        self.max = create_user('max')
        self.lisa = create_user('lisa')
        self.website = create_offer(self.max)
        self.logo = create_offer(self.lisa, 'Logo', 'Schnelles Logo')
        self.logo.details.filter(offer_type='basic').update(
            price=50, delivery_time_in_days=2)
        yesterday = timezone.now() - timedelta(days=1)
        Offer.objects.filter(pk=self.website.pk).update(updated_at=yesterday)

    def get_ids(self, params=None):
        """Request the list and return the IDs of the results."""
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [offer['id'] for offer in response.data['results']]

    def test_list_is_public(self):
        """Anonymous users get a paginated list."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)

    def test_list_fields(self):
        """Each offer has exactly the documented fields."""
        offer = self.client.get(self.url).data['results'][0]
        self.assertEqual(set(offer), LIST_FIELDS)

    def test_details_contain_id_and_url(self):
        """Details only contain the ID and the URL of each package."""
        offer = self.client.get(self.url).data['results'][-1]
        detail = self.website.details.get(offer_type='basic')
        self.assertEqual(len(offer['details']), 3)
        self.assertIn(
            {'id': detail.pk, 'url': f'/offerdetails/{detail.pk}/'},
            offer['details'])

    def test_min_values_are_calculated(self):
        """min_price and min_delivery_time come from the details."""
        offer = self.client.get(self.url).data['results'][-1]
        self.assertEqual(offer['min_price'], 100)
        self.assertEqual(offer['min_delivery_time'], 5)

    def test_user_details(self):
        """user_details contains the name of the creator."""
        offer = self.client.get(self.url).data['results'][-1]
        self.assertEqual(offer['user_details'], {
            'first_name': 'Max', 'last_name': 'Muster', 'username': 'max'})

    def test_filter_creator_id(self):
        """creator_id only returns offers of this user."""
        ids = self.get_ids({'creator_id': self.max.pk})
        self.assertEqual(ids, [self.website.pk])

    def test_filter_min_price(self):
        """min_price only returns offers that cost at least this value."""
        ids = self.get_ids({'min_price': 80})
        self.assertEqual(ids, [self.website.pk])

    def test_filter_max_delivery_time(self):
        """max_delivery_time returns offers deliverable in time."""
        ids = self.get_ids({'max_delivery_time': 3})
        self.assertEqual(ids, [self.logo.pk])

    def test_search_title_and_description(self):
        """search looks into title and description."""
        self.assertEqual(self.get_ids({'search': 'logo'}), [self.logo.pk])
        self.assertEqual(
            self.get_ids({'search': 'professionell'}), [self.website.pk])

    def test_ordering_min_price(self):
        """ordering sorts by the calculated minimum price."""
        ids = self.get_ids({'ordering': 'min_price'})
        self.assertEqual(ids, [self.logo.pk, self.website.pk])
        ids = self.get_ids({'ordering': '-min_price'})
        self.assertEqual(ids, [self.website.pk, self.logo.pk])

    def test_ordering_updated_at(self):
        """ordering sorts by the date of the last change."""
        ids = self.get_ids({'ordering': 'updated_at'})
        self.assertEqual(ids, [self.website.pk, self.logo.pk])

    def test_empty_params_are_ignored(self):
        """The frontend always sends all params, often empty."""
        params = {'creator_id': '', 'search': '', 'ordering': '',
                  'max_delivery_time': '', 'page': 1}
        self.assertEqual(len(self.get_ids(params)), 2)

    def test_default_page_size_matches_frontend(self):
        """Without page_size the list returns 6 offers per page."""
        for number in range(6):
            create_offer(self.max, f'Offer {number}')
        response = self.client.get(self.url)
        self.assertEqual(len(response.data['results']), 6)
        self.assertIsNotNone(response.data['next'])

    def test_page_size_param(self):
        """page_size limits the number of results per page."""
        response = self.client.get(self.url, {'page_size': 1})
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['count'], 2)

    def test_invalid_params(self):
        """Non-numeric values for numeric filters return 400."""
        for param in ['creator_id', 'min_price', 'max_delivery_time']:
            response = self.client.get(self.url, {param: 'abc'})
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, param)
