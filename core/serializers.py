"""Serializer helpers shared by several apps."""
from rest_framework import serializers


class RejectUnknownFieldsMixin:
    """Return 400 for request fields the serializer does not offer."""

    def validate(self, attrs):
        """Reject every sent field that is not part of the serializer."""
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: 'This field cannot be changed.' for field in unknown})
        return super().validate(attrs)
