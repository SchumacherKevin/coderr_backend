"""Serializers for the reviews_app API."""
from rest_framework import serializers

from profile_app.models import UserProfile
from reviews_app.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """A review; the reviewer is always the logged-in user."""

    class Meta:
        model = Review
        fields = [
            'id', 'business_user', 'reviewer', 'rating', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['reviewer', 'created_at', 'updated_at']

    def validate_business_user(self, value):
        """Only business users can be reviewed."""
        profile = getattr(value, 'profile', None)
        if not profile or profile.type != UserProfile.ProfileType.BUSINESS:
            raise serializers.ValidationError('This user is not a business.')
        return value

    def validate(self, attrs):
        """A customer may review each business user only once."""
        reviewer = self.context['request'].user
        if Review.objects.filter(
                business_user=attrs['business_user'],
                reviewer=reviewer).exists():
            raise serializers.ValidationError(
                'You have already reviewed this business user.')
        return attrs
