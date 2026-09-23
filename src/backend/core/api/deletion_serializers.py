"""Serializers for batch deletion metadata."""

# These serializers validate/read metadata; they never create or update models.
# pylint: disable=abstract-method

from rest_framework import serializers


class ItemsDeletionInfoRequestSerializer(serializers.Serializer):
    """Validate and deduplicate the items in a deletion preflight."""

    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)

    def validate_ids(self, value):
        """Keep one entry for each requested item."""
        return list(dict.fromkeys(value))


class ItemDeletionInfoSerializer(serializers.Serializer):
    """Extensible metadata for a single item's deletion."""

    hasRestrictedDescendent = serializers.BooleanField(source="has_restricted_descendent")
