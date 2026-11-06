"""Serializers for the offers_app API."""
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from offers_app.models import Offer, OfferDetail


class OfferDetailLinkSerializer(serializers.ModelSerializer):
    """ID and relative URL of one package, as shown in the offer list."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']

    def get_url(self, obj):
        """Return the relative URL of the offer detail."""
        return f'/offerdetails/{obj.pk}/'


class UserDetailsSerializer(serializers.ModelSerializer):
    """Name of the offer creator."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']


class OfferListSerializer(serializers.ModelSerializer):
    """Offer with links to its details and the calculated minimum values."""

    details = OfferDetailLinkSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = UserDetailsSerializer(source='user', read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id', 'user', 'title', 'image', 'description', 'created_at',
            'updated_at', 'details', 'min_price', 'min_delivery_time',
            'user_details',
        ]


class OfferDetailSerializer(serializers.ModelSerializer):
    """All fields of one package."""

    features = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = OfferDetail
        fields = [
            'id', 'title', 'revisions', 'delivery_time_in_days', 'price',
            'features', 'offer_type',
        ]


class OfferWriteSerializer(serializers.ModelSerializer):
    """Create an offer together with its three details."""

    details = OfferDetailSerializer(many=True)

    class Meta:
        model = Offer
        fields = ['id', 'title', 'image', 'description', 'details']

    def validate_details(self, value):
        """Require exactly one detail each for basic, standard, premium."""
        types = sorted(detail['offer_type'] for detail in value)
        if types != sorted(OfferDetail.OfferType.values):
            raise serializers.ValidationError(
                'An offer needs exactly one basic, standard and premium '
                'detail.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create the offer first, then its details."""
        details = validated_data.pop('details')
        offer = Offer.objects.create(**validated_data)
        OfferDetail.objects.bulk_create(
            OfferDetail(offer=offer, **detail) for detail in details)
        return offer
