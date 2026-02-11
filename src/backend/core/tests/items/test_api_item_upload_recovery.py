"""Tests for deterministic upload recovery patterns (pending TTL + retry)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_item_retrieve_pending_over_ttl_is_expired(settings):
    """A pending item past the TTL should be surfaced deterministically as EXPIRED."""
    settings.ITEM_UPLOAD_PENDING_TTL_SECONDS = 60

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="a.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    item.upload_state = models.ItemUploadStateChoices.PENDING
    item.upload_started_at = timezone.now() - timedelta(seconds=61)
    item.save(update_fields=["upload_state", "upload_started_at", "updated_at"])

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_state"] == models.ItemUploadStateChoices.EXPIRED
    assert payload["url"] is None
    assert payload["url_preview"] is None


def test_api_item_upload_ended_rejects_expired_pending(settings):
    """Ending an upload on an expired pending item should be deterministic and actionable."""
    settings.ITEM_UPLOAD_PENDING_TTL_SECONDS = 60

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="a.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    item.upload_state = models.ItemUploadStateChoices.PENDING
    item.upload_started_at = timezone.now() - timedelta(seconds=61)
    item.save(update_fields=["upload_state", "upload_started_at", "updated_at"])

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "code": "item_upload_state_expired",
                "detail": "This upload session has expired. Please retry the upload.",
                "attr": "item",
            }
        ],
    }

    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.EXPIRED


def test_api_item_upload_policy_refreshes_pending_window(settings):
    """Re-initiating upload should return a fresh policy and refresh upload_started_at."""
    settings.ITEM_UPLOAD_PENDING_TTL_SECONDS = 60

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="a.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    old_started_at = timezone.now() - timedelta(seconds=61)
    item.upload_state = models.ItemUploadStateChoices.PENDING
    item.upload_started_at = old_started_at
    item.save(update_fields=["upload_state", "upload_started_at", "updated_at"])

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-policy/")

    assert response.status_code == 200
    payload = response.json()
    assert "policy" in payload
    assert isinstance(payload["policy"], str)
    assert payload["policy"]

    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.PENDING
    assert item.upload_started_at is not None
    assert item.upload_started_at > old_started_at
