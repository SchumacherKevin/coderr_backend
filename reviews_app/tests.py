"""Tests for the reviews_app models."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from offers_app.tests import create_user
from reviews_app.models import Review


def create_review(business_user, reviewer, rating=4, **fields):
    """Create a review of the reviewer for the business user."""
    return Review.objects.create(
        business_user=business_user, reviewer=reviewer, rating=rating,
        description=fields.pop('description', 'Alles war toll!'), **fields)


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
