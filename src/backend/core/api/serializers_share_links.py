"""Serializers for token-enforced public share links (unauthenticated)."""

from __future__ import annotations

from urllib.parse import quote, urlencode

from django.conf import settings

from rest_framework import serializers

from core import models
from core.api import utils


class PublicShareItemSerializer(serializers.ModelSerializer):
    """Public-facing item serializer for share link browsing."""

    upload_state = serializers.SerializerMethodField(read_only=True)
    url = serializers.SerializerMethodField(read_only=True)
    url_preview = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Item
        fields = [
            "id",
            "title",
            "type",
            "filename",
            "mimetype",
            "size",
            "created_at",
            "updated_at",
            "upload_state",
            "url",
            "url_preview",
        ]
        read_only_fields = fields

    def _share_query(self) -> str:
        token = self.context.get("share_token")
        if not token:
            return ""
        return urlencode({"share_token": token})

    def _with_share_token(self, base_url: str | None) -> str | None:
        if not base_url:
            return None
        q = self._share_query()
        if not q:
            return base_url
        return f"{base_url}?{q}"

    def get_upload_state(self, item):
        """Return the effective upload state (pending TTL applied deterministically)."""
        return item.effective_upload_state()

    def get_url(self, item):
        """Return the token-bound media URL for a shared file (or None)."""
        effective_upload_state = item.effective_upload_state()
        if (
            item.type != models.ItemTypeChoices.FILE
            or effective_upload_state
            in {
                models.ItemUploadStateChoices.PENDING,
                models.ItemUploadStateChoices.EXPIRED,
            }
            or item.filename is None
        ):
            return None

        base = f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL}{quote(item.file_key)}"
        return self._with_share_token(base)

    def get_url_preview(self, item):
        """Return the token-bound preview URL for a shared file (or None)."""
        effective_upload_state = item.effective_upload_state()
        if (
            item.type != models.ItemTypeChoices.FILE
            or effective_upload_state
            in {
                models.ItemUploadStateChoices.PENDING,
                models.ItemUploadStateChoices.EXPIRED,
            }
            or item.filename is None
            or not utils.is_previewable_item(item)
        ):
            return None

        base = f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL_PREVIEW}{quote(item.file_key)}"
        return self._with_share_token(base)
