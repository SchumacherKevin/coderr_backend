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


class OfferDetailHyperlinkSerializer(serializers.ModelSerializer):
    """ID and absolute URL of one package, as shown for a single offer."""

    url = serializers.HyperlinkedIdentityField(
        view_name='offerdetail-detail')

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']


class OfferRetrieveSerializer(serializers.ModelSerializer):
    """Single offer with links to its details and its minimum values."""

    details = OfferDetailHyperlinkSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id', 'user', 'title', 'image', 'description', 'created_at',
            'updated_at', 'details', 'min_price', 'min_delivery_time',
        ]


class OfferListSerializer(OfferRetrieveSerializer):
    """Offer in the list: relative detail links and creator names."""

    details = OfferDetailLinkSerializer(many=True, read_only=True)
    user_details = UserDetailsSerializer(source='user', read_only=True)

    class Meta(OfferRetrieveSerializer.Meta):
        fields = OfferRetrieveSerializer.Meta.fields + ['user_details']


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
    """Create or update an offer together with its details."""

    details = OfferDetailSerializer(many=True)

    class Meta:
        model = Offer
        fields = ['id', 'title', 'image', 'description', 'details']

    def validate_details(self, value):
        """Check the details for creating or for updating an offer."""
        if self.instance:
            return self.validate_detail_update(value)
        types = sorted(detail['offer_type'] for detail in value)
        if types != sorted(OfferDetail.OfferType.values):
            raise serializers.ValidationError(
                'An offer needs exactly one basic, standard and premium '
                'detail.')
        return value

    def validate_detail_update(self, value):
        """Each changed detail needs a unique offer_type to be found."""
        types = [detail.get('offer_type') for detail in value]
        if None in types or len(set(types)) != len(types):
            raise serializers.ValidationError(
                'Each detail needs a unique offer_type.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create the offer first, then its details."""
        details = validated_data.pop('details')
        offer = Offer.objects.create(**validated_data)
        OfferDetail.objects.bulk_create(
            OfferDetail(offer=offer, **detail) for detail in details)
        return offer

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update the offer and the sent details, found by offer_type."""
        details = validated_data.pop('details', [])
        instance = super().update(instance, validated_data)
        for detail_data in details:
            self.update_detail(instance, detail_data)
        return instance

    def update_detail(self, offer, detail_data):
        """Overwrite the sent fields of one detail, its ID stays the same."""
        detail = offer.details.filter(
            offer_type=detail_data['offer_type']).first()
        if detail is None:
            raise serializers.ValidationError(
                {'details': 'This offer has no detail of this offer_type.'})
        for attr, value in detail_data.items():
            setattr(detail, attr, value)
        detail.save()
