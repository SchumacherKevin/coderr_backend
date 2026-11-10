"""Tests for the base_info_app API endpoint."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from offers_app.tests import create_offer, create_user
from reviews_app.tests import create_review


class BaseInfoTests(APITestCase):
    """Tests for GET /api/base-info/."""

    def setUp(self):
        """The endpoint is public, so nobody logs in."""
        self.url = reverse('base-info')

    def test_empty_database(self):
        """Without data every value is 0, also the average rating."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'review_count': 0, 'average_rating': 0,
            'business_profile_count': 0, 'offer_count': 0})

    def test_counts_platform_data(self):
        """Counts reviews, business profiles and offers."""
        max_user, lisa = create_user('max'), create_user('lisa')
        anna = create_user('anna', 'customer')
        tom = create_user('tom', 'customer')
        create_offer(max_user)
        create_offer(max_user, 'Logo')
        create_offer(lisa)
        create_review(max_user, anna, rating=4)
        create_review(lisa, anna, rating=5)
        create_review(max_user, tom, rating=5)
        response = self.client.get(self.url)
        self.assertEqual(response.data, {
            'review_count': 3, 'average_rating': 4.7,
            'business_profile_count': 2, 'offer_count': 3})

    def test_average_rating_is_rounded(self):
        """average_rating has one decimal place."""
        business = create_user('max')
        create_review(business, create_user('anna', 'customer'), rating=4)
        create_review(business, create_user('tom', 'customer'), rating=3)
        create_review(business, create_user('eva', 'customer'), rating=3)
        response = self.client.get(self.url)
        self.assertEqual(response.data['average_rating'], 3.3)

    def test_stale_token_is_ignored(self):
        """An old token in the header does not block the public endpoint."""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_not_allowed(self):
        """The endpoint only supports GET."""
        response = self.client.post(self.url, {})
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
