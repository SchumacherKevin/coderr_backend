"""Tests for the offers_app models and API endpoints."""
import shutil
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.testing import AdminQueryCountMixin, QueryCountMixin
from offers_app.models import Offer, OfferDetail
from profile_app.models import UserProfile
from profile_app.tests import TEMP_MEDIA_ROOT, create_test_image

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


def offer_detail_url(pk):
    """Return the URL of a single offer detail."""
    return reverse('offerdetail-detail', kwargs={'pk': pk})


def offer_url(pk):
    """Return the URL of a single offer."""
    return reverse('offer-detail', kwargs={'pk': pk})


def detail_payload(offer_type, price=100, **fields):
    """Return the request data for one offer detail."""
    data = {
        'title': f'{offer_type.title()} Design', 'revisions': 2,
        'delivery_time_in_days': 5, 'price': price,
        'features': ['Logo Design', 'Visitenkarte'],
        'offer_type': offer_type,
    }
    data.update(fields)
    return data


def offer_payload():
    """Return valid request data for an offer with three details."""
    return {
        'title': 'Grafikdesign-Paket',
        'image': None,
        'description': 'Ein umfassendes Grafikdesign-Paket.',
        'details': [
            detail_payload('basic'),
            detail_payload('standard', 200, revisions=5),
            detail_payload('premium', 500, revisions=-1),
        ],
    }


class OfferCreateTests(APITestCase):
    """Tests for POST /api/offers/."""

    def setUp(self):
        """Log in as a business user."""
        self.url = reverse('offer-list')
        self.business = create_user('max')
        self.client.force_authenticate(user=self.business)

    def post(self, data):
        """Send the offer data as JSON."""
        return self.client.post(self.url, data, format='json')

    def test_create_offer(self):
        """A business user creates an offer with three details."""
        response = self.post(offer_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        offer = Offer.objects.get()
        self.assertEqual(offer.user, self.business)
        self.assertEqual(offer.details.count(), 3)

    def test_create_response_format(self):
        """The response contains the offer and full details with IDs."""
        data = self.post(offer_payload()).data
        self.assertEqual(
            set(data), {'id', 'title', 'image', 'description', 'details'})
        detail = data['details'][0]
        self.assertEqual(set(detail), {
            'id', 'title', 'revisions', 'delivery_time_in_days', 'price',
            'features', 'offer_type'})
        self.assertEqual(detail['price'], 100)
        self.assertEqual(detail['features'], ['Logo Design', 'Visitenkarte'])

    def test_create_without_details(self):
        """An offer without details is rejected."""
        data = offer_payload()
        del data['details']
        self.assertEqual(
            self.post(data).status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_two_details(self):
        """An offer needs exactly three details."""
        data = offer_payload()
        data['details'].pop()
        response = self.post(data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Offer.objects.count(), 0)

    def test_create_with_duplicate_offer_type(self):
        """basic, standard and premium must each appear once."""
        data = offer_payload()
        data['details'][2]['offer_type'] = 'basic'
        self.assertEqual(
            self.post(data).status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_invalid_detail(self):
        """A detail with missing price or invalid values is rejected."""
        data = offer_payload()
        del data['details'][0]['price']
        data['details'][1]['features'] = 'kein Array'
        response = self.post(data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(OfferDetail.objects.count(), 0)

    def test_create_without_title(self):
        """The title is required."""
        data = offer_payload()
        del data['title']
        self.assertEqual(
            self.post(data).status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.post(offer_payload())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_as_customer(self):
        """Customers are not allowed to create offers."""
        self.client.force_authenticate(user=create_user('anna', 'customer'))
        response = self.post(offer_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Offer.objects.count(), 0)

    def assert_detail_rejected(self, **fields):
        """A basic detail with these values must return 400."""
        data = offer_payload()
        data['details'][0].update(fields)
        response = self.post(data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Offer.objects.count(), 0)

    def test_create_with_negative_price(self):
        """A negative price is rejected."""
        self.assert_detail_rejected(price=-50)

    def test_create_with_zero_delivery_time(self):
        """The delivery time needs at least one day."""
        self.assert_detail_rejected(delivery_time_in_days=0)

    def test_create_with_revisions_below_minus_one(self):
        """-1 means unlimited revisions, lower values are rejected."""
        self.assert_detail_rejected(revisions=-2)

    def test_create_with_zero_price_and_unlimited_revisions(self):
        """Price 0 and -1 revisions (unlimited) are allowed."""
        data = offer_payload()
        data['details'][0].update(price=0, revisions=-1)
        response = self.post(data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_as_user_without_profile(self):
        """Users without a profile (e.g. admins) get 403."""
        admin = User.objects.create_user(username='admin', password='x')
        self.client.force_authenticate(user=admin)
        response = self.post(offer_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OfferDetailRetrieveTests(APITestCase):
    """Tests for GET /api/offerdetails/{id}/."""

    def setUp(self):
        """Create an offer and log in as a customer."""
        offer = create_offer(create_user('max'))
        self.detail = offer.details.get(offer_type='basic')
        self.url = offer_detail_url(self.detail.pk)
        self.client.force_authenticate(user=create_user('anna', 'customer'))

    def test_get_offer_detail(self):
        """Logged-in users get all fields of the package."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'id': self.detail.pk, 'title': 'basic Design', 'revisions': 2,
            'delivery_time_in_days': 5, 'price': 100,
            'features': ['Logo Design'], 'offer_type': 'basic'})

    def test_get_offer_detail_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_unknown_offer_detail(self):
        """An unknown ID returns 404."""
        response = self.client.get(offer_detail_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_offer_detail_is_read_only(self):
        """Offer details can only be read here, not changed."""
        response = self.client.patch(self.url, {'price': 1})
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class OfferSingleTestBase(APITestCase):
    """Shared setup: an offer of max, logged in as max."""

    def setUp(self):
        """Create the offer and log in as its creator."""
        self.owner = create_user('max')
        self.offer = create_offer(self.owner)
        self.url = offer_url(self.offer.pk)
        self.client.force_authenticate(user=self.owner)

    def login_as_other_user(self):
        """Log in as a business user that does not own the offer."""
        self.client.force_authenticate(user=create_user('lisa'))


class OfferRetrieveTests(OfferSingleTestBase):
    """Tests for GET /api/offers/{id}/."""

    def test_get_offer(self):
        """Every logged-in user gets the offer with the documented fields."""
        self.login_as_other_user()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), LIST_FIELDS - {'user_details'})
        self.assertEqual(response.data['user'], self.owner.pk)
        self.assertEqual(response.data['min_price'], 100)
        self.assertEqual(response.data['min_delivery_time'], 5)

    def test_details_contain_absolute_url(self):
        """Details link to the offer detail endpoint with a full URL."""
        detail = self.offer.details.get(offer_type='basic')
        details = self.client.get(self.url).data['details']
        expected_url = 'http://testserver' + offer_detail_url(detail.pk)
        self.assertIn({'id': detail.pk, 'url': expected_url}, details)

    def test_get_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_unknown_offer(self):
        """An unknown ID returns 404."""
        response = self.client.get(offer_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class OfferUpdateTests(OfferSingleTestBase):
    """Tests for PATCH /api/offers/{id}/."""

    @classmethod
    def tearDownClass(cls):
        """Remove the uploaded test images."""
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def patch(self, data):
        """Send the changes as JSON."""
        return self.client.patch(self.url, data, format='json')

    def test_patch_detail_with_negative_price(self):
        """The limits for detail values also apply to PATCH."""
        response = self.patch({'details': [detail_payload('basic', -1)]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_title(self):
        """Only the given fields change."""
        response = self.patch({'title': 'Neuer Titel'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.title, 'Neuer Titel')
        self.assertEqual(self.offer.description, 'Professionelles Design')

    def test_patch_response_contains_full_details(self):
        """The response has all fields and the full details."""
        data = self.patch({'title': 'Neuer Titel'}).data
        self.assertEqual(
            set(data), {'id', 'title', 'image', 'description', 'details'})
        self.assertEqual(len(data['details']), 3)
        self.assertIn('price', data['details'][0])

    def test_patch_detail_keeps_id(self):
        """A detail is found by offer_type and keeps its ID."""
        basic = self.offer.details.get(offer_type='basic')
        changes = detail_payload('basic', 120, title='Basic Updated',
                                 features=['Logo Design', 'Flyer'])
        response = self.patch({'details': [changes]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated = self.offer.details.get(offer_type='basic')
        self.assertEqual(updated.pk, basic.pk)
        self.assertEqual(updated.title, 'Basic Updated')
        self.assertEqual(updated.price, Decimal('120.00'))
        self.assertEqual(OfferDetail.objects.count(), 3)

    def test_patch_detail_partially(self):
        """Fields of a detail that are not sent stay unchanged."""
        self.patch({'details': [{'offer_type': 'premium', 'price': 450}]})
        premium = self.offer.details.get(offer_type='premium')
        self.assertEqual(premium.price, Decimal('450.00'))
        self.assertEqual(premium.delivery_time_in_days, 10)

    def test_patch_other_details_unchanged(self):
        """Details that are not sent stay unchanged."""
        self.patch({'details': [{'offer_type': 'basic', 'price': 1}]})
        standard = self.offer.details.get(offer_type='standard')
        self.assertEqual(standard.price, Decimal('200.00'))

    def test_patch_detail_without_offer_type(self):
        """offer_type is needed to identify the detail."""
        response = self.patch({'details': [{'price': 1}]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_detail_with_invalid_value(self):
        """Invalid values in a detail return 400 and change nothing."""
        response = self.patch({'title': 'Neu', 'details': [
            {'offer_type': 'basic', 'price': 'teuer'}]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.title, 'Website Design')

    def test_patch_duplicate_offer_type(self):
        """The same offer_type may not appear twice."""
        response = self.patch({'details': [
            {'offer_type': 'basic', 'price': 1},
            {'offer_type': 'basic', 'price': 2}]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_upload_image(self):
        """The frontend uploads the image as multipart in its own PATCH."""
        response = self.client.patch(
            self.url, {'image': create_test_image()}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.offer.refresh_from_db()
        self.assertTrue(self.offer.image.name.startswith('offer_images/'))

    def test_patch_other_users_offer(self):
        """Only the creator may change the offer."""
        self.login_as_other_user()
        response = self.patch({'title': 'Gekapert'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.patch({'title': 'Neu'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_unknown_offer(self):
        """An unknown ID returns 404."""
        response = self.client.patch(
            offer_url(999), {'title': 'Neu'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_not_allowed(self):
        """Only PATCH is supported for changes."""
        response = self.client.put(self.url, offer_payload(), format='json')
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class OfferDeleteTests(OfferSingleTestBase):
    """Tests for DELETE /api/offers/{id}/."""

    def test_delete_own_offer(self):
        """The creator deletes the offer together with its details."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Offer.objects.count(), 0)
        self.assertEqual(OfferDetail.objects.count(), 0)

    def test_delete_other_users_offer(self):
        """Only the creator may delete the offer."""
        self.login_as_other_user()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Offer.objects.count(), 1)

    def test_delete_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_unknown_offer(self):
        """An unknown ID returns 404."""
        response = self.client.delete(offer_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


def create_offer_of_new_user():
    """Create an offer of a new business user for the query count tests."""
    return create_offer(create_user(f'user{User.objects.count()}'), 'Logo')


class OfferQueryCountTests(QueryCountMixin, APITestCase):
    """The offer endpoints do not run one query per offer or detail."""

    def setUp(self):
        """Create one offer and log in as its creator."""
        self.owner = create_user('max')
        self.offer = create_offer(self.owner)
        self.client.force_authenticate(user=self.owner)

    def test_offer_list(self):
        """More offers of other users do not add queries."""
        self.assert_queries_constant(
            reverse('offer-list'), create_offer_of_new_user)

    def count_patch_queries(self, offer_types):
        """PATCH the price of the given details, return the query count."""
        details = [{'offer_type': t, 'price': 300} for t in offer_types]
        with CaptureQueriesContext(connection) as context:
            self.client.patch(offer_url(self.offer.pk),
                              {'details': details}, format='json')
        return len(context)

    def test_patch_details_only_adds_updates(self):
        """Each further detail in a PATCH costs only its own UPDATE."""
        one = self.count_patch_queries(['basic'])
        three = self.count_patch_queries(['basic', 'standard', 'premium'])
        self.assertEqual(three - one, 2)


class OfferAdminQueryCountTests(AdminQueryCountMixin, TestCase):
    """The offer admin lists do not run one query per row."""

    def setUp(self):
        """Log in as admin and create one offer."""
        self.login_as_admin()
        create_offer_of_new_user()

    def test_offer_changelist(self):
        """More offers do not add queries to the offer list."""
        self.assert_queries_constant(
            reverse('admin:offers_app_offer_changelist'),
            create_offer_of_new_user)

    def test_offerdetail_changelist(self):
        """More offers do not add queries to the offer detail list."""
        self.assert_queries_constant(
            reverse('admin:offers_app_offerdetail_changelist'),
            create_offer_of_new_user)
