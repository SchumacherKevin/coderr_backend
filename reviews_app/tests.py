"""Tests for the reviews_app models and API endpoints."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.testing import AdminQueryCountMixin
from offers_app.tests import create_user
from reviews_app.models import Review

REVIEW_FIELDS = {
    'id', 'business_user', 'reviewer', 'rating', 'description',
    'created_at', 'updated_at',
}


def create_review(business_user, reviewer, rating=4, **fields):
    """Create a review of the reviewer for the business user."""
    return Review.objects.create(
        business_user=business_user, reviewer=reviewer, rating=rating,
        description=fields.pop('description', 'Alles war toll!'), **fields)


def review_url(pk):
    """Return the URL of a single review."""
    return reverse('review-detail', kwargs={'pk': pk})


class ReviewModelTests(TestCase):
    """Tests for the Review model."""

    def setUp(self):
        """Create a business user with one review of a customer."""
        self.business = create_user('max')
        self.customer = create_user('anna', 'customer')
        self.review = create_review(self.business, self.customer)

    def test_review_stores_values(self):
        """Rating, description and timestamps are stored."""
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.description, 'Alles war toll!')
        self.assertIsNotNone(self.review.created_at)
        self.assertIsNotNone(self.review.updated_at)

    def test_related_names(self):
        """Business user and reviewer reach their reviews."""
        self.assertEqual(
            list(self.business.received_reviews.all()), [self.review])
        self.assertEqual(
            list(self.customer.written_reviews.all()), [self.review])

    def test_one_review_per_business_user(self):
        """A customer can review a business user only once."""
        with self.assertRaises(IntegrityError):
            create_review(self.business, self.customer, rating=1)

    def test_same_reviewer_for_other_business_user(self):
        """The same customer may review another business user."""
        create_review(create_user('lisa'), self.customer)
        self.assertEqual(Review.objects.count(), 2)

    def test_rating_between_one_and_five(self):
        """Ratings outside 1 to 5 are invalid."""
        for rating in [0, 6]:
            self.review.rating = rating
            with self.assertRaises(ValidationError):
                self.review.full_clean()

    def test_description_defaults_to_empty_string(self):
        """Without description the field is an empty string."""
        review = Review.objects.create(
            business_user=create_user('lisa'), reviewer=self.customer,
            rating=5)
        self.assertEqual(review.description, '')

    def test_delete_reviewer_deletes_reviews(self):
        """Deleting the reviewer also deletes his reviews."""
        self.customer.delete()
        self.assertEqual(Review.objects.count(), 0)

    def test_newest_review_comes_first(self):
        """Reviews are ordered by updated_at, newest first."""
        newer = create_review(create_user('lisa'), self.customer)
        Review.objects.filter(pk=self.review.pk).update(
            updated_at=self.review.updated_at.replace(year=2020))
        self.assertEqual(list(Review.objects.all()), [newer, self.review])

    def test_str(self):
        """Readable name for the admin."""
        self.assertEqual(str(self.review), 'anna -> max (4)')


class ReviewTestBase(APITestCase):
    """Shared setup: two business users and two customers."""

    def setUp(self):
        """Create the users and log in as the customer anna."""
        self.business = create_user('max')
        self.other_business = create_user('lisa')
        self.customer = create_user('anna', 'customer')
        self.other_customer = create_user('tom', 'customer')
        self.list_url = reverse('review-list')
        self.client.force_authenticate(user=self.customer)


class ReviewListTests(ReviewTestBase):
    """Tests for GET /api/reviews/."""

    def setUp(self):
        """Create three reviews with different ratings and dates."""
        super().setUp()
        self.old = create_review(self.business, self.customer, rating=5)
        self.middle = create_review(self.other_business, self.customer, 2)
        self.new = create_review(self.business, self.other_customer, 3)
        for days, review in enumerate([self.new, self.middle, self.old]):
            Review.objects.filter(pk=review.pk).update(
                updated_at=timezone.now() - timedelta(days=days))

    def get_ids(self, params=None):
        """Request the list and return the IDs of the reviews."""
        response = self.client.get(self.list_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [review['id'] for review in response.data]

    def test_list_all_reviews(self):
        """Without filters all reviews are returned as a plain list."""
        self.assertEqual(
            self.get_ids(), [self.new.pk, self.middle.pk, self.old.pk])

    def test_list_fields(self):
        """Each review has exactly the documented fields."""
        review = self.client.get(self.list_url).data[0]
        self.assertEqual(set(review), REVIEW_FIELDS)

    def test_filter_business_user_id(self):
        """business_user_id returns the reviews of this business user."""
        ids = self.get_ids({'business_user_id': self.business.pk})
        self.assertEqual(ids, [self.new.pk, self.old.pk])

    def test_filter_reviewer_id(self):
        """reviewer_id returns the reviews written by this user."""
        ids = self.get_ids({'reviewer_id': self.customer.pk})
        self.assertEqual(ids, [self.middle.pk, self.old.pk])

    def test_ordering_rating(self):
        """ordering sorts by rating."""
        ids = self.get_ids({'ordering': 'rating'})
        self.assertEqual(ids, [self.middle.pk, self.new.pk, self.old.pk])

    def test_ordering_updated_at(self):
        """ordering sorts by the date of the last change."""
        ids = self.get_ids({'ordering': 'updated_at'})
        self.assertEqual(ids, [self.old.pk, self.middle.pk, self.new.pk])

    def test_empty_params_are_ignored(self):
        """Empty filter values do not filter."""
        ids = self.get_ids({'business_user_id': '', 'ordering': ''})
        self.assertEqual(len(ids), 3)

    def test_invalid_filter(self):
        """Non-numeric IDs return 400."""
        response = self.client.get(self.list_url, {'reviewer_id': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReviewCreateTests(ReviewTestBase):
    """Tests for POST /api/reviews/."""

    def post(self, data=None):
        """Send the review data as JSON."""
        data = data or {'business_user': self.business.pk, 'rating': 4,
                        'description': 'Alles war toll!'}
        return self.client.post(self.list_url, data, format='json')

    def test_create_review(self):
        """A customer reviews a business user, he becomes the reviewer."""
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data), REVIEW_FIELDS)
        self.assertEqual(response.data['reviewer'], self.customer.pk)
        self.assertEqual(Review.objects.get().business_user, self.business)

    def test_reviewer_cannot_be_set(self):
        """The reviewer always is the logged-in user."""
        response = self.post({'business_user': self.business.pk,
                              'rating': 4, 'reviewer': self.other_customer.pk})
        self.assertEqual(response.data['reviewer'], self.customer.pk)

    def test_second_review_is_rejected(self):
        """A customer can review a business user only once."""
        self.post()
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Review.objects.count(), 1)

    def test_invalid_rating(self):
        """The rating must be between 1 and 5."""
        for rating in [0, 6, 'gut']:
            response = self.post(
                {'business_user': self.business.pk, 'rating': rating})
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, rating)

    def test_review_for_customer_is_rejected(self):
        """Only business users can be reviewed."""
        response = self.post(
            {'business_user': self.other_customer.pk, 'rating': 4})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_for_unknown_user(self):
        """An unknown business_user returns 400."""
        response = self.post({'business_user': 999, 'rating': 4})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_as_business_user(self):
        """Business users may not write reviews."""
        self.client.force_authenticate(user=self.other_business)
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReviewSingleTestBase(ReviewTestBase):
    """Shared setup: a review of anna for max."""

    def setUp(self):
        """Create the review, anna stays logged in."""
        super().setUp()
        self.review = create_review(self.business, self.customer)
        self.url = review_url(self.review.pk)

    def login_as_other_customer(self):
        """Log in as a customer who did not write the review."""
        self.client.force_authenticate(user=self.other_customer)


class ReviewUpdateTests(ReviewSingleTestBase):
    """Tests for PATCH /api/reviews/{id}/."""

    def patch(self, data, url=None):
        """Send the changes as JSON."""
        return self.client.patch(url or self.url, data, format='json')

    def test_reviewer_updates_review(self):
        """The reviewer changes rating and description."""
        response = self.patch(
            {'rating': 5, 'description': 'Noch besser als erwartet!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), REVIEW_FIELDS)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.description, 'Noch besser als erwartet!')

    def test_patch_only_description(self):
        """Fields that are not sent stay unchanged."""
        self.patch({'description': 'Kurz'})
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)

    def test_patch_other_fields(self):
        """Only rating and description may be changed."""
        response = self.patch(
            {'rating': 5, 'business_user': self.other_business.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.review.refresh_from_db()
        self.assertEqual(self.review.business_user, self.business)

    def test_patch_invalid_rating(self):
        """The rating must stay between 1 and 5."""
        response = self.patch({'rating': 9})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_other_users_review(self):
        """Only the reviewer may change the review."""
        self.login_as_other_customer()
        response = self.patch({'rating': 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.patch({'rating': 1})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_unknown_review(self):
        """An unknown ID returns 404."""
        response = self.patch({'rating': 1}, review_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReviewDeleteTests(ReviewSingleTestBase):
    """Tests for DELETE /api/reviews/{id}/."""

    def test_reviewer_deletes_review(self):
        """The reviewer deletes the review."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Review.objects.count(), 0)

    def test_delete_other_users_review(self):
        """Only the reviewer may delete the review."""
        self.login_as_other_customer()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 1)

    def test_delete_unauthenticated(self):
        """Anonymous users get 401."""
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_unknown_review(self):
        """An unknown ID returns 404."""
        response = self.client.delete(review_url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReviewQueryCountTests(AdminQueryCountMixin, ReviewTestBase):
    """Review list and review admin do not run one query per review."""

    def setUp(self):
        """Create one review of anna."""
        super().setUp()
        create_review(self.business, self.customer)

    def create_review(self):
        """Create a review of a new customer."""
        customer = create_user(f'customer{Review.objects.count()}', 'customer')
        create_review(self.business, customer)

    def test_review_list(self):
        """More reviews do not add queries to the review list."""
        self.assert_queries_constant(self.list_url, self.create_review)

    def test_review_changelist(self):
        """More reviews do not add queries to the admin review list."""
        self.login_as_admin()
        self.assert_queries_constant(
            reverse('admin:reviews_app_review_changelist'),
            self.create_review)
