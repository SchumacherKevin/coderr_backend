"""Serializer helpers shared by several apps."""
from rest_framework import serializers


class RejectUnknownFieldsMixin:
    """Return 400 for sent fields that are unknown or read-only."""

    def validate(self, attrs):
        """Reject every sent field the serializer cannot write."""
        writable = {
            name for name, field in self.fields.items()
            if not field.read_only
        }
        unknown = set(self.initial_data) - writable
        if unknown:
            raise serializers.ValidationError(
                {field: 'This field cannot be changed.' for field in unknown})
        return super().validate(attrs)
