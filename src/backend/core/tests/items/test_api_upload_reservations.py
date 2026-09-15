"""Security properties of quota reservations and size-bound upload authorizations."""

from io import BytesIO
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api.utils import generate_upload_policy
from core.entitlements import get_entitlements_backend
from core.entitlements.backends.deploycenter import ENTITLEMENTS_CACHE_KEY_PREFIX
from core.storage import get_storage_compute_backend
from core.storage.cache import get_storage_used_cache_key

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def local_quota(settings):
    """Use small, real quotas instead of mocking the admission decision."""
    settings.ENTITLEMENTS_BACKEND = "core.entitlements.backends.local.LocalEntitlementsBackend"
    settings.ENTITLEMENTS_BACKEND_PARAMETERS = {"default_storage_limit": 100}
    get_entitlements_backend.cache_clear()


def create_upload(client, size, parent=None):
    """Use the public API to reserve bytes, without sending anything to storage."""
    url = f"/api/v1.0/items/{parent.pk}/children/" if parent else "/api/v1.0/items/"
    return client.post(
        url, {"type": "file", "filename": "reserved.txt", "expected_size": size}, format="json"
    )


@pytest.mark.parametrize("in_folder", [False, True])
def test_reservation_is_counted_before_any_upload(in_folder, django_capture_on_commit_callbacks):
    """An abandoned upload consumes the quota on both creation routes."""
    user = factories.UserFactory()
    parent = (
        factories.ItemFactory(type="folder", users=[(user, models.RoleChoices.OWNER)])
        if in_folder
        else None
    )
    client = APIClient()
    client.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        response = create_upload(client, 80, parent)
    assert response.status_code == 201
    item = models.Item.objects.get(pk=response.data["id"])
    assert item.expected_size == 80
    assert item.size is None
    assert item.upload_state == models.ItemUploadStateChoices.PENDING
    assert get_storage_compute_backend().compute_storage_used([user]) == 80
    response = create_upload(client, 21, parent)
    assert response.status_code == 403
    assert response.data["errors"][0]["code"] == "user_quota_exceeded"
    assert models.Item.objects.filter(creator=user, expected_size__isnull=False).count() == 1


def test_cached_usage_is_accepted_until_creation_invalidates_it(django_capture_on_commit_callbacks):
    """A cached permission can overshoot; persisted reservations block the next fresh check."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, type="file", size=90)
    cache_key = get_storage_used_cache_key(user.pk)
    cache.set(cache_key, 0)
    client = APIClient()
    client.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        assert create_upload(client, 11).status_code == 201
    assert cache.get(cache_key) is None
    assert get_storage_compute_backend().compute_storage_used([user]) == 101
    assert create_upload(client, 1).status_code == 403
    assert get_storage_compute_backend().compute_storage_used([user]) == 101


@pytest.mark.parametrize("size", [-1, None, "invalid", 1.5, True])
def test_invalid_reservation_does_not_issue_policy(size):
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    assert create_upload(client, size).status_code == 400
    assert not models.Item.objects.exists()


def test_missing_reservation_is_rejected():
    client = APIClient()
    client.force_authenticate(factories.UserFactory())
    response = client.post("/api/v1.0/items/", {"type": "file", "filename": "missing.txt"})
    assert response.status_code == 400
    assert response.data["errors"][0]["attr"] == "expected_size"
    assert not models.Item.objects.exists()


def test_per_file_limit_even_for_unlimited_account(settings):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 10
    client = APIClient()
    client.force_authenticate(factories.UserFactory(storage_limit_override=0))
    assert create_upload(client, 11).status_code == 400
    assert create_upload(client, 10).status_code == 201


@pytest.mark.parametrize("acl", ["private", "default"])
def test_put_signature_binds_content_length(settings, acl):
    settings.AWS_S3_UPLOAD_ACL = acl
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    response = create_upload(client, 10)
    assert response.status_code == 201
    policy = response.data["policy"]
    headers = parse_qs(urlparse(policy).query)["X-Amz-SignedHeaders"][0].split(";")
    assert "content-length" in headers
    assert ("x-amz-acl" in headers) == (acl == "private")
    item = models.Item.objects.get(pk=response.data["id"])
    item.expected_size = 11
    assert generate_upload_policy(item) != policy


def test_legacy_item_cannot_receive_an_unbounded_policy():
    with pytest.raises(ValueError, match="reservation"):
        generate_upload_policy(factories.ItemFactory(type="file"))


def test_legacy_signature_configuration_cannot_issue_unbounded_put(settings):
    settings.AWS_S3_SIGNATURE_VERSION = "s3"
    item = factories.ItemFactory(type="file", expected_size=8)
    with pytest.raises(ImproperlyConfigured, match="signed Content-Length"):
        generate_upload_policy(item)


def test_failed_creation_rolls_back_the_reservation():
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    create_child = models.Item.objects.create_child

    def fail_after_insert(**kwargs):
        create_child(**kwargs)
        raise RuntimeError("creation failed")

    with mock.patch.object(models.Item.objects, "create_child", side_effect=fail_after_insert):
        with pytest.raises(RuntimeError, match="creation failed"):
            create_upload(client, 100)
    assert get_storage_compute_backend().compute_storage_used([user]) == 0
    assert not models.Item.objects.exists()


@pytest.mark.parametrize("size", [0, 99])
def test_finalize_full_quota_once(size, django_capture_on_commit_callbacks):
    """An admitted reservation can complete after the quota becomes full."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    response = create_upload(client, size)
    assert response.status_code == 201
    item = models.Item.objects.get(pk=response.data["id"])
    default_storage.save(item.file_key, BytesIO(b"x" * size))
    with django_capture_on_commit_callbacks(execute=True):
        factories.ItemFactory(creator=user, type="file", size=100 - size)
    assert get_entitlements_backend().can_upload(user)["result"] is False
    editor = factories.UserFactory(storage_limit_override=1)
    factories.ItemFactory(creator=editor, size=10)
    factories.UserItemAccessFactory(item=item, user=editor, role="editor")
    client.force_authenticate(editor)
    with (
        mock.patch("core.api.viewsets.malware_detection.analyse_file") as scan,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post(f"/api/v1.0/items/{item.pk}/upload-ended/")
        assert response.status_code == 200
    scan.assert_called_once_with(item.file_key, item_id=item.pk)
    with mock.patch("core.api.viewsets.malware_detection.analyse_file") as scan:
        assert client.post(f"/api/v1.0/items/{item.pk}/upload-ended/").status_code == 200
    scan.assert_not_called()
    item.refresh_from_db()
    assert item.size == size
    assert get_storage_compute_backend().compute_storage_used([user]) == 100


def test_actual_size_must_match_reservation():
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    response = create_upload(client, 10)
    item = models.Item.objects.get(pk=response.data["id"])
    # Simulate an incompatible provider accepting more than the signed length.
    default_storage.save(item.file_key, BytesIO(b"x" * 11))
    with mock.patch("core.api.viewsets.process_item_purge.delay"):
        response = client.post(f"/api/v1.0/items/{item.pk}/upload-ended/")
    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "file_size_mismatch"
    item.refresh_from_db()
    assert item.hard_deleted_at is not None


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("cache_hit", [True, False])
def test_deploycenter_uses_cached_decision_or_fetches_reserved_usage(settings, allowed, cache_hit):
    """Cached decisions are reused; a cache miss sends the reservation to DeployCenter."""
    settings.ENTITLEMENTS_BACKEND = (
        "core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend"
    )
    settings.ENTITLEMENTS_BACKEND_PARAMETERS = {
        "base_url": "https://entitlements.test",
        "service_id": 1,
        "api_key": "test",
    }
    get_entitlements_backend.cache_clear()
    user = factories.UserFactory(claims={"siret": "org"})
    colleague = factories.UserFactory(claims={"siret": "org"})
    factories.ItemFactory(creator=colleague, type="file", expected_size=90)
    cache_key = f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user.pk}"
    client = APIClient()
    client.force_authenticate(user)
    decision = {
        "entitlements": {
            "can_upload": allowed,
            "can_upload_reason": None if allowed else "organization_quota_exceeded",
            # Drive must not reimplement these limits, even if they appear inconsistent.
            "max_storage_account": 1 if allowed else 1000,
            "max_storage_organization": 1 if allowed else 1000,
        }
    }
    if cache_hit:
        cache.set(cache_key, decision)
    with mock.patch("core.entitlements.backends.deploycenter.requests.post") as post:
        post.return_value.json.return_value = decision
        response = create_upload(client, 20)
    if cache_hit:
        post.assert_not_called()
    else:
        post.assert_called_once()
        metrics = post.call_args.kwargs["json"]["usage_metrics"]
        assert metrics[0]["metrics"]["storage_used"] == 20
        assert metrics[1]["metrics"]["storage_used"] == 110
    assert response.status_code == (201 if allowed else 403)
    if not allowed:
        assert response.data["errors"][0]["code"] == "organization_quota_exceeded"
        assert "policy" not in response.data
    assert models.Item.objects.filter(creator=user).exists() is allowed
    assert get_storage_compute_backend().compute_storage_used([user]) == (20 if allowed else 0)
    assert cache.get(cache_key) == decision


@pytest.mark.parametrize("size", [99, 100, 101])
def test_admission_preserves_can_upload_threshold_and_rolls_back(size):
    """The existing local decision rejects a reached or exceeded quota."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    response = create_upload(client, size)
    allowed = size < 100
    assert response.status_code == (201 if allowed else 403)
    assert models.Item.objects.filter(creator=user).exists() is allowed
    assert get_storage_compute_backend().compute_storage_used([user]) == (size if allowed else 0)


def test_can_upload_failure_rolls_back_without_publishing_a_policy():
    """A failed provider request must leave neither an item nor reserved bytes."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)

    def unavailable(checked_user):
        assert checked_user == user
        assert get_storage_compute_backend().compute_storage_used([user]) == 80
        raise RuntimeError("provider unavailable")

    with (
        mock.patch.object(get_entitlements_backend(), "can_upload", side_effect=unavailable),
        mock.patch("core.api.utils.generate_upload_policy") as policy,
    ):
        with pytest.raises(RuntimeError, match="provider unavailable"):
            create_upload(client, 80)
    policy.assert_not_called()
    assert not models.Item.objects.exists()
    assert get_storage_compute_backend().compute_storage_used([user]) == 0
