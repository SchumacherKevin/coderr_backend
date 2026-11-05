"""Serializers for the profile_app API."""
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from profile_app.models import UserProfile


class ProfileSerializer(serializers.ModelSerializer):
    """Profile data combined with the related user fields."""

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(
        source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(
        source='user.last_name', required=False, allow_blank=True)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours', 'type',
            'email', 'created_at',
        ]
        read_only_fields = ['user', 'type', 'created_at']

    def validate_email(self, value):
        """Reject an email address that belongs to another user."""
        users = User.objects.filter(email__iexact=value)
        if users.exclude(pk=self.instance.user.pk).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        """Save the user fields on the user and the rest on the profile."""
        user_data = validated_data.pop('user', {})
        self.update_user(instance.user, user_data)
        return super().update(instance, validated_data)

    def update_user(self, user, user_data):
        """Write first_name, last_name and email onto the Django user."""
        for attr, value in user_data.items():
            setattr(user, attr, value)
        if user_data:
            user.save(update_fields=list(user_data))


class BusinessProfileListSerializer(serializers.ModelSerializer):
    """Business profile as shown in the business list."""

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(
        source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours', 'type',
        ]


class CustomerProfileListSerializer(serializers.ModelSerializer):
    """Customer profile as shown in the customer list."""

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(
        source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    uploaded_at = serializers.DateTimeField(
        source='created_at', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'username', 'first_name', 'last_name', 'file',
            'uploaded_at', 'type',
        ]
