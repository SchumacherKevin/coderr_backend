"""Serializers for the auth_app API."""
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from profile_app.models import UserProfile


class RegistrationSerializer(serializers.ModelSerializer):
    """Validates registration data and creates user, profile and token."""

    repeated_password = serializers.CharField(write_only=True)
    type = serializers.ChoiceField(choices=UserProfile.ProfileType.choices)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'repeated_password', 'type']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, value):
        """Reject an email address that is already registered."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    def validate(self, attrs):
        """Ensure both password fields match."""
        if attrs['password'] != attrs['repeated_password']:
            raise serializers.ValidationError(
                {'repeated_password': 'Passwords do not match.'}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create the user with a hashed password, its profile and a token."""
        validated_data.pop('repeated_password')
        profile_type = validated_data.pop('type')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user, type=profile_type)
        Token.objects.create(user=user)
        return user
