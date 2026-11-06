"""Serializers for the orders_app API."""
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from offers_app.models import OfferDetail
from orders_app.models import Order

COPIED_FIELDS = [
    'title', 'revisions', 'delivery_time_in_days', 'price', 'features',
    'offer_type',
]


class OrderSerializer(serializers.ModelSerializer):
    """All fields of an order."""

    class Meta:
        model = Order
        fields = [
            'id', 'customer_user', 'business_user', *COPIED_FIELDS,
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """Create an order from an offer detail ID."""

    offer_detail_id = serializers.IntegerField(write_only=True)

    def create(self, validated_data):
        """Copy the package data; the customer is the logged-in user."""
        detail = get_object_or_404(
            OfferDetail.objects.select_related('offer'),
            pk=validated_data['offer_detail_id'])
        copied = {field: getattr(detail, field) for field in COPIED_FIELDS}
        return Order.objects.create(
            customer_user=self.context['request'].user,
            business_user=detail.offer.user, **copied)

    def to_representation(self, instance):
        """Return the created order with all its fields."""
        return OrderSerializer(instance, context=self.context).data
