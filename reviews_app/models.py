"""Models of reviews_app."""
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """Rating of a business user written by a customer."""

    business_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_reviews')
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='written_reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        constraints = [
            models.UniqueConstraint(
                fields=['business_user', 'reviewer'],
                name='unique_review_per_business_user',
            ),
        ]

    def __str__(self):
        """String representation of the review."""
        return (f'{self.reviewer.username} -> '
                f'{self.business_user.username} ({self.rating})')
