"""
Tests for upload reservations in drive's core app: quota reservations and
size-bound upload authorizations.
"""

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
    url = f"/api/v1.0/items/{parent.pk!s}/children/" if parent else "/api/v1.0/items/"

    return client.post(
        url,
        {"type": "file", "filename": "reserved.txt", "size": size},
        format="json",
    )


@pytest.mark.parametrize("in_folder", [False, True])
def test_api_upload_reservations_counted_before_any_upload(
    in_folder, django_capture_on_commit_callbacks
):
    """An abandoned upload consumes the quota on both creation routes."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = (
        factories.ItemFactory(type="folder", users=[(user, models.RoleChoices.OWNER)])
        if in_folder
        else None
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = create_upload(client, 80, parent)

    assert response.status_code == 201
    assert response.data["size"] == 80

    item = models.Item.objects.get(pk=response.data["id"])
    assert item.size == 80
    assert item.upload_state == models.ItemUploadStateChoices.PENDING
    assert get_storage_compute_backend().compute_storage_used([user]) == 80

    # The reserved bytes are already counted, so the next reservation is refused.
    response = create_upload(client, 21, parent)

    assert response.status_code == 403
    assert response.data["errors"][0]["code"] == "user_quota_exceeded"
    assert models.Item.objects.filter(creator=user, size__isnull=False).count() == 1


def test_api_upload_reservations_cached_usage_invalidated_on_creation(
    django_capture_on_commit_callbacks,
):
    """
    A cached usage can let a reservation overshoot the quota, but the creation must
    invalidate that cache so that the next check sees the persisted reservations.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory(creator=user, type="file", size=90)
    cache_key = get_storage_used_cache_key(user.pk)
    cache.set(cache_key, 0)

    with django_capture_on_commit_callbacks(execute=True):
        response = create_upload(client, 11)

    assert response.status_code == 201
    assert cache.get(cache_key) is None
    assert get_storage_compute_backend().compute_storage_used([user]) == 101

    assert create_upload(client, 1).status_code == 403
    assert get_storage_compute_backend().compute_storage_used([user]) == 101


@pytest.mark.parametrize("size", [-1, None, "invalid", 1.5, True])
def test_api_upload_reservations_invalid_size(size):
    """An invalid reservation should be refused before any item or policy is created."""
    client = APIClient()
    client.force_login(factories.UserFactory())

    response = create_upload(client, size)

    assert response.status_code == 400
    assert not models.Item.objects.exists()


def test_api_upload_reservations_missing_size():
    """Creating a file item without reserving a size should be refused."""
    client = APIClient()
    client.force_login(factories.UserFactory())

    response = client.post("/api/v1.0/items/", {"type": "file", "filename": "missing.txt"})

    assert response.status_code == 400
    assert response.data["errors"][0]["attr"] == "size"
    assert not models.Item.objects.exists()


def test_api_upload_reservations_per_file_limit_for_unlimited_account(settings):
    """An account without a storage limit is still bound by the per-file limit."""
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 10

    client = APIClient()
    client.force_login(factories.UserFactory(storage_limit_override=0))

    assert create_upload(client, 11).status_code == 400
    assert create_upload(client, 10).status_code == 201


@pytest.mark.parametrize("acl", ["private", "default"])
def test_api_upload_reservations_policy_binds_content_length(settings, acl):
    """
    The upload policy should sign the reserved size, so a client cannot reuse it to
    send a file of a different length.
    """
    settings.AWS_S3_UPLOAD_ACL = acl

    client = APIClient()
    client.force_login(factories.UserFactory())

    response = create_upload(client, 10)

    assert response.status_code == 201

    policy = response.data["policy"]
    headers = parse_qs(urlparse(policy).query)["X-Amz-SignedHeaders"][0].split(";")

    assert "content-length" in headers
    assert ("x-amz-acl" in headers) == (acl == "private")

    item = models.Item.objects.get(pk=response.data["id"])
    item.size = 11

    assert generate_upload_policy(item) != policy


def test_api_upload_reservations_policy_requires_a_reservation():
    """An item created before reservations existed should not get an unbounded policy."""
    item = factories.ItemFactory(type="file")

    with pytest.raises(ValueError, match="reservation"):
        generate_upload_policy(item)


def test_api_upload_reservations_policy_requires_signature_v4(settings):
    """
    A signature version that cannot sign the content length should be refused, as it
    would issue an unbounded PUT.
    """
    # The signature version is read from the settings only when a replacement domain
    # builds a dedicated client: the storage client is connected once and would keep
    # signing with the version it was built with.
    settings.AWS_S3_DOMAIN_REPLACE = "http://storage.test"
    settings.AWS_S3_SIGNATURE_VERSION = "s3"
    item = factories.ItemFactory(type="file", size=8)

    with pytest.raises(ImproperlyConfigured, match="signed Content-Length"):
        generate_upload_policy(item)


def test_api_upload_reservations_rollback_on_creation_failure():
    """A creation failing after the insert should not leave any reserved bytes."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    create_child = models.Item.objects.create_child

    def fail_after_insert(**kwargs):
        create_child(**kwargs)
        raise RuntimeError("creation failed")

    with mock.patch.object(models.Item.objects, "create_child", side_effect=fail_after_insert):
        with pytest.raises(RuntimeError, match="creation failed"):
            create_upload(client, 100)

    assert not models.Item.objects.exists()
    assert get_storage_compute_backend().compute_storage_used([user]) == 0


@pytest.mark.parametrize("size", [0, 99])
def test_api_upload_reservations_upload_ended_with_full_quota(
    size, django_capture_on_commit_callbacks
):
    """An admitted reservation should still complete once the quota is full."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = create_upload(client, size)

    assert response.status_code == 201

    item = models.Item.objects.get(pk=response.data["id"])
    default_storage.save(item.file_key, BytesIO(b"x" * size))

    # Fill the creator's quota while the upload is still pending.
    with django_capture_on_commit_callbacks(execute=True):
        factories.ItemFactory(creator=user, type="file", size=100 - size)

    assert get_entitlements_backend().can_upload(user)["result"] is False

    editor = factories.UserFactory(storage_limit_override=1)
    factories.ItemFactory(creator=editor, size=10)
    factories.UserItemAccessFactory(item=item, user=editor, role="editor")
    client.force_login(editor)

    with (
        mock.patch("core.api.viewsets.malware_detection.analyse_file") as mock_analyse_file,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post(f"/api/v1.0/items/{item.pk!s}/upload-ended/")

    assert response.status_code == 200
    mock_analyse_file.assert_called_once_with(item.file_key, item_id=item.pk)

    # The upload can only be ended once, so the quota cannot be consumed twice.
    with mock.patch("core.api.viewsets.malware_detection.analyse_file") as mock_analyse_file:
        response = client.post(f"/api/v1.0/items/{item.pk!s}/upload-ended/")

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "item_upload_state_not_pending"
    mock_analyse_file.assert_not_called()

    item.refresh_from_db()
    assert item.size == size
    assert get_storage_compute_backend().compute_storage_used([user]) == 100


@pytest.mark.parametrize("actual_size", [9, 11])
def test_api_upload_reservations_upload_ended_size_mismatch(actual_size):
    """A file that does not match its reservation should be rejected and purged."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = create_upload(client, 10)
    item = models.Item.objects.get(pk=response.data["id"])

    # Simulate an incompatible provider accepting a different length.
    default_storage.save(item.file_key, BytesIO(b"x" * actual_size))

    with mock.patch("core.api.viewsets.process_item_purge.delay"):
        response = client.post(f"/api/v1.0/items/{item.pk!s}/upload-ended/")

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "file_size_mismatch"

    item.refresh_from_db()
    assert item.hard_deleted_at is not None
    assert item.size == 10


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("cache_hit", [True, False])
def test_api_upload_reservations_deploycenter_decision(settings, allowed, cache_hit):
    """
    Cached DeployCenter decisions should be reused, while a cache miss should send the
    reserved bytes along with the usage metrics.
    """
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
    factories.ItemFactory(creator=colleague, type="file", size=90)

    client = APIClient()
    client.force_login(user)

    decision = {
        "entitlements": {
            "can_upload": allowed,
            "can_upload_reason": None if allowed else "organization_quota_exceeded",
            # Drive must not reimplement these limits, even if they appear inconsistent.
            "max_storage_account": 1 if allowed else 1000,
            "max_storage_organization": 1 if allowed else 1000,
        }
    }
    cache_key = f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user.pk!s}"
    if cache_hit:
        cache.set(cache_key, decision)

    with mock.patch("core.entitlements.backends.deploycenter.requests.post") as mock_post:
        mock_post.return_value.json.return_value = decision
        response = create_upload(client, 20)

    if cache_hit:
        mock_post.assert_not_called()
    else:
        mock_post.assert_called_once()
        metrics = mock_post.call_args.kwargs["json"]["usage_metrics"]
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
def test_api_upload_reservations_local_quota_threshold(size):
    """A reservation reaching or exceeding the local quota should be rolled back."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = create_upload(client, size)

    allowed = size < 100
    assert response.status_code == (201 if allowed else 403)
    assert models.Item.objects.filter(creator=user).exists() is allowed
    assert get_storage_compute_backend().compute_storage_used([user]) == (size if allowed else 0)


def test_api_upload_reservations_rollback_on_entitlements_failure():
    """A failing entitlements provider must leave neither an item nor reserved bytes."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    def unavailable(checked_user):
        # The bytes are reserved before the decision, so the provider sees them.
        assert checked_user == user
        assert get_storage_compute_backend().compute_storage_used([user]) == 80
        raise RuntimeError("provider unavailable")

    with (
        mock.patch.object(get_entitlements_backend(), "can_upload", side_effect=unavailable),
        mock.patch("core.api.utils.generate_upload_policy") as mock_generate_upload_policy,
    ):
        with pytest.raises(RuntimeError, match="provider unavailable"):
            create_upload(client, 80)

    mock_generate_upload_policy.assert_not_called()
    assert not models.Item.objects.exists()
    assert get_storage_compute_backend().compute_storage_used([user]) == 0


@pytest.mark.parametrize(
    "state", [models.ItemUploadStateChoices.PENDING, models.ItemUploadStateChoices.READY]
)
@pytest.mark.parametrize("method", ["patch", "put"])
def test_api_upload_reservations_size_read_only_on_update(state, method):
    """Updating an item should not reduce its reservation nor change the signed size."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = create_upload(client, 80)

    assert response.status_code == 201

    item = models.Item.objects.get(pk=response.data["id"])
    item.upload_state = state
    item.save(update_fields=["upload_state"])

    response = getattr(client, method)(
        f"/api/v1.0/items/{item.pk!s}/",
        {"title": item.title, "size": 0},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["size"] == 80

    item.refresh_from_db()
    assert item.size == 80
    assert get_storage_compute_backend().compute_storage_used([user]) == 80


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "folder", "title": "Folder", "size": 0},
        {"type": "file", "title": "Document", "extension": "odt", "size": 0},
    ],
)
def test_api_upload_reservations_size_rejected_for_folders_and_templates(payload):
    """Only uploaded files should reserve bytes, folders and templates should not."""
    client = APIClient()
    client.force_login(factories.UserFactory())

    response = client.post("/api/v1.0/items/", payload, format="json")

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "unexpected_upload_size"
    assert not models.Item.objects.exists()
