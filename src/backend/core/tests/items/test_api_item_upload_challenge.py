"""Tests for the upload possession challenge (deduplication proof of ownership)."""

import hashlib
from io import BytesIO

from django.core.cache import cache
from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def _create_item_with_hash(client, content, size=None):
    """Create a file item announcing the hash of content."""
    upload_hash = hashlib.sha256(content).hexdigest()
    response = client.post(
        "/api/v1.0/items/",
        {
            "size": size if size is not None else len(content),
            "type": models.ItemTypeChoices.FILE,
            "filename": "big.bin",
            "upload_hash": upload_hash,
        },
        format="json",
    )
    assert response.status_code == 201
    item = models.Item.objects.get(id=response.json()["id"])
    return item, response, upload_hash


def _proof_for(content, challenge):
    """SHA-256 of the challenged byte range of content."""
    start = challenge["offset"]
    return hashlib.sha256(content[start : start + challenge["length"]]).hexdigest()


def test_upload_challenge_issued_above_threshold(settings):
    """Above the threshold, creation returns a challenge instead of a policy."""
    settings.UPLOAD_CHALLENGE_THRESHOLD_BYTES = 100
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item, response, _ = _create_item_with_hash(client, b"x" * 200)

    challenge = response.json()["upload_challenge"]
    assert challenge is not None
    assert challenge["length"] == min(settings.UPLOAD_CHALLENGE_RANGE_BYTES, 200)
    assert 0 <= challenge["offset"] <= 200 - challenge["length"]
    assert response.json()["policy"] is None
    assert cache.get(f"upload-challenge:{item.id!s}") == challenge


def test_no_challenge_below_threshold(settings):
    """Below the threshold, creation returns the policy directly, no challenge."""
    settings.UPLOAD_CHALLENGE_THRESHOLD_BYTES = 1000
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item, response, _ = _create_item_with_hash(client, b"x" * 200)

    assert response.json()["upload_challenge"] is None
    assert response.json()["policy"] is not None
    assert cache.get(f"upload-challenge:{item.id!s}") is None


def test_upload_challenge_success_attaches_blob(settings):
    """A valid proof on an existing safe blob attaches the item, READY, no upload."""
    settings.UPLOAD_CHALLENGE_THRESHOLD_BYTES = 100
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    content = bytes(range(200))
    item, response, upload_hash = _create_item_with_hash(client, content, size=200)
    blob = factories.BlobFactory(
        hash=upload_hash,
        size=len(content),
        upload_state=models.ItemUploadStateChoices.READY,
    )
    default_storage.save(blob.file_key, BytesIO(content))

    challenge = response.json()["upload_challenge"]
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/upload-challenge/",
        {"proof": _proof_for(content, challenge)},
        format="json",
    )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.blob_id == blob.id
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size == len(content)


def test_upload_challenge_wrong_proof_returns_policy(settings):
    """A wrong proof returns the upload policy, like when no blob exists."""
    settings.UPLOAD_CHALLENGE_THRESHOLD_BYTES = 100
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    content = bytes(range(200))
    item, response, upload_hash = _create_item_with_hash(client, content, size=200)
    blob = factories.BlobFactory(
        hash=upload_hash,
        size=len(content),
        upload_state=models.ItemUploadStateChoices.READY,
    )
    default_storage.save(blob.file_key, BytesIO(content))

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/upload-challenge/",
        {"proof": hashlib.sha256(b"not the content").hexdigest()},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["policy"] is not None
    item.refresh_from_db()
    assert item.blob_id is None
    assert item.upload_state == models.ItemUploadStateChoices.PENDING


def test_upload_challenge_no_blob_returns_policy(settings):
    """No blob for the announced hash: same response as a failed challenge."""
    settings.UPLOAD_CHALLENGE_THRESHOLD_BYTES = 100
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    content = bytes(range(200))
    item, response, _ = _create_item_with_hash(client, content, size=200)
    challenge = response.json()["upload_challenge"]

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/upload-challenge/",
        {"proof": _proof_for(content, challenge)},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["policy"] is not None
    item.refresh_from_db()
    assert item.blob_id is None


def test_upload_challenge_is_single_use(settings):
    """The challenge is consumed by the first attempt: a replay gets a 400."""
    settings.UPLOAD_CHALLENGE_THRESHOLD_BYTES = 100
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    content = bytes(range(200))
    item, response, _ = _create_item_with_hash(client, content, size=200)
    challenge = response.json()["upload_challenge"]
    proof = _proof_for(content, challenge)

    first = client.post(
        f"/api/v1.0/items/{item.id!s}/upload-challenge/", {"proof": proof}, format="json"
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1.0/items/{item.id!s}/upload-challenge/", {"proof": proof}, format="json"
    )
    assert second.status_code == 400
    assert second.json()["errors"][0]["code"] == "no_active_challenge"
