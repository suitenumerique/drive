"""Serializers for mount browse endpoints (contract-level)."""

from __future__ import annotations

from rest_framework import serializers

# pylint: disable=abstract-method


class MountEntryAbilitiesSerializer(serializers.Serializer):
    """Per-entry abilities used by the Explorer to avoid dead actions."""

    children_list = serializers.BooleanField()
    upload = serializers.BooleanField()
    download = serializers.BooleanField()
    preview = serializers.BooleanField()
    wopi = serializers.BooleanField()
    share_link_create = serializers.BooleanField()


class MountEntrySerializer(serializers.Serializer):
    """Serialize a virtual mount entry identified by (mount_id, normalized_path)."""

    mount_id = serializers.CharField()
    normalized_path = serializers.CharField()
    entry_type = serializers.ChoiceField(choices=["file", "folder"])
    name = serializers.CharField()
    size = serializers.IntegerField(required=False, allow_null=True)
    modified_at = serializers.DateTimeField(required=False, allow_null=True)
    abilities = MountEntryAbilitiesSerializer()


class MountBrowseChildrenSerializer(serializers.Serializer):
    """Limit/offset paginated children payload (DRF-compatible)."""

    count = serializers.IntegerField()
    next = serializers.CharField(required=False, allow_null=True)
    previous = serializers.CharField(required=False, allow_null=True)
    results = MountEntrySerializer(many=True)


class MountBrowseResponseSerializer(serializers.Serializer):
    """Browse response: current entry + children if folder."""

    mount_id = serializers.CharField()
    normalized_path = serializers.CharField()
    capabilities = serializers.DictField(child=serializers.BooleanField())
    entry = MountEntrySerializer()
    children = MountBrowseChildrenSerializer(allow_null=True)
