"""Serializers for E2E tests."""

from rest_framework import serializers


# Suppress the warning about not implementing `create` and `update` methods
# since we don't use a model and only rely on the serializer for validation
# pylint: disable=abstract-method
class E2EAuthSerializer(serializers.Serializer):
    """Serializer for E2E authentication."""

    email = serializers.EmailField(required=True)
