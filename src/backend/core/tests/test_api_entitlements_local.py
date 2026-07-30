"""
Test Entitlements API endpoints with Local entitlements backend.
"""

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.entitlements.backends.local import (
    DEFAULT_STORAGE_LIMIT,
    LocalEntitlementsBackend,
)
from core.storage.cache import get_storage_used_cache_key

pytestmark = pytest.mark.django_db

LOCAL_BACKEND = "core.entitlements.backends.local.LocalEntitlementsBackend"


def backdate_user(user, created_at):
    """Backdate a user's creation date (created_at is auto_now_add)."""
    models.User.objects.filter(pk=user.pk).update(created_at=created_at)
    user.refresh_from_db()


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={},
)
def test_api_entitlements_local_anonymous():
    """Anonymous users should not be allowed to get entitlements."""
    client = APIClient()
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 401
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={},
)
def test_api_entitlements_local_defaults_no_usage():
    """Without parameters, users get the default 10 GiB limit and no usage."""
    client = APIClient()
    user = factories.UserFactory()
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {"result": True},
        "can_upload": {"result": True},
        "quota": {
            "state": "default",
            "usage": 0,
            "limit": DEFAULT_STORAGE_LIMIT,
        },
        "context": {},
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_under_limit():
    """Users under the default limit can upload and see their usage."""
    client = APIClient()
    user = factories.UserFactory()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=400)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {"result": True}
    assert response.json()["quota"] == {
        "state": "default",
        "usage": 400,
        "limit": 1000,
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_over_default_limit():
    """Users over the default limit cannot upload but still see the gauge."""
    client = APIClient()
    user = factories.UserFactory()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=1500)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "user_quota_exceeded",
        "message": "You have exceeded your storage limit.",
    }
    assert response.json()["quota"] == {
        "state": "default",
        "usage": 1500,
        "limit": 1000,
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_at_exact_limit():
    """Users exactly at the limit cannot start a new upload."""
    client = APIClient()
    user = factories.UserFactory()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=1000)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"]["result"] is False


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_override_raises_limit():
    """A per-user override higher than the default limit takes precedence."""
    client = APIClient()
    user = factories.UserFactory(storage_limit_override=5000)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=1500)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {"result": True}
    assert response.json()["quota"] == {
        "state": "default",
        "usage": 1500,
        "limit": 5000,
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_override_exceeded():
    """Users exceeding their own override get a dedicated reason."""
    client = APIClient()
    user = factories.UserFactory(storage_limit_override=500)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=600)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "user_override_quota_exceeded",
        "message": "You have exceeded your storage limit.",
    }
    assert response.json()["quota"] == {
        "state": "default",
        "usage": 600,
        "limit": 500,
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_override_zero_unlimited():
    """An override set to 0 means unlimited storage and no quota gauge."""
    client = APIClient()
    user = factories.UserFactory(storage_limit_override=0)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=10**12)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {"result": True}
    assert "quota" not in response.json()


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "default_storage_limit": 1000,
        "exempt_users_created_before": "2026-01-01T00:00:00+00:00",
    },
)
def test_api_entitlements_local_grandfathered_user():
    """Users created before the cutoff have no limit and no quota gauge."""
    client = APIClient()
    user = factories.UserFactory()
    backdate_user(user, "2025-12-31T23:59:59+00:00")
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=10**12)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {"result": True}
    assert "quota" not in response.json()


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "default_storage_limit": 1000,
        "exempt_users_created_before": "2026-01-01T00:00:00+00:00",
    },
)
def test_api_entitlements_local_user_created_after_cutoff():
    """Users created after the cutoff are limited normally."""
    client = APIClient()
    user = factories.UserFactory()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=1500)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"]["result"] is False
    assert response.json()["quota"] == {
        "state": "default",
        "usage": 1500,
        "limit": 1000,
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "default_storage_limit": 1000,
        "exempt_users_created_before": "2026-01-01T00:00:00+00:00",
    },
)
def test_api_entitlements_local_override_beats_grandfathering():
    """A per-user override applies even to users created before the cutoff."""
    client = APIClient()
    user = factories.UserFactory(storage_limit_override=500)
    backdate_user(user, "2025-12-31T23:59:59+00:00")
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=600)
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "user_override_quota_exceeded",
        "message": "You have exceeded your storage limit.",
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_usage_excludes_hard_deleted():
    """Hard deleted items should not count against the quota."""
    client = APIClient()
    user = factories.UserFactory()
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=1500)
    models.Item.objects.filter(pk=item.pk).update(hard_deleted_at=timezone.now())
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {"result": True}
    assert response.json()["quota"] == {
        "state": "default",
        "usage": 0,
        "limit": 1000,
    }


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_upload_blocked_via_items_api():
    """Creating a file item over quota should be denied with the backend message."""
    user = factories.UserFactory()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=1500)

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="editor", item__type=models.ItemTypeChoices.FOLDER
    )
    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "type": models.ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
    )
    assert response.status_code == 403
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                # The can_upload reason is exposed as the error code so the
                # frontend can show a specific, translatable message.
                "code": "user_quota_exceeded",
                "detail": "You have exceeded your storage limit.",
                "attr": None,
            }
        ],
    }


def test_api_entitlements_local_invalid_cutoff_parameter():
    """An unparseable cutoff datetime should raise ImproperlyConfigured."""
    with pytest.raises(ImproperlyConfigured):
        LocalEntitlementsBackend(exempt_users_created_before="not-a-date")


def test_api_entitlements_local_naive_cutoff_parameter_made_aware():
    """A naive ISO cutoff should be accepted and made timezone-aware."""
    backend = LocalEntitlementsBackend(exempt_users_created_before="2026-01-01T00:00:00")
    assert timezone.is_aware(backend.exempt_users_created_before)


def test_api_entitlements_local_invalid_default_storage_limit():
    """A non-positive default storage limit should raise ImproperlyConfigured."""
    with pytest.raises(ImproperlyConfigured):
        LocalEntitlementsBackend(default_storage_limit=0)


def test_api_entitlements_local_string_default_storage_limit():
    """A default storage limit passed as a string should be coerced to int."""
    backend = LocalEntitlementsBackend(default_storage_limit="1000")
    assert backend.default_storage_limit == 1000


def test_api_entitlements_local_invalid_cache_timeout():
    """A non-positive cache timeout should raise ImproperlyConfigured."""
    with pytest.raises(ImproperlyConfigured):
        LocalEntitlementsBackend(cache_timeout=0)


def test_api_entitlements_local_string_cache_timeout():
    """A cache timeout passed as a string should be coerced to int."""
    backend = LocalEntitlementsBackend(cache_timeout="60")
    assert backend.cache_timeout == 60


def test_api_entitlements_local_can_upload_anonymous():
    """Anonymous users cannot upload, even with an exemption cutoff configured."""
    backend = LocalEntitlementsBackend(exempt_users_created_before="2026-01-01T00:00:00+00:00")
    assert backend.can_upload(AnonymousUser()) == {"result": False}


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_usage_is_cached():
    """The storage used should be cached and reused on subsequent calls."""
    client = APIClient()
    user = factories.UserFactory()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=400)
    client.force_authenticate(user)

    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 400
    assert cache.get(get_storage_used_cache_key(user.id)) == 400

    # Poison the cache to prove the next call reads from it instead of the database.
    cache.set(get_storage_used_cache_key(user.id), 999)
    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 999


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_zero_usage_is_cached():
    """A zero usage should be cached, not treated as a cache miss."""
    client = APIClient()
    user = factories.UserFactory()
    client.force_authenticate(user)

    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 0
    assert cache.get(get_storage_used_cache_key(user.id), "MISS") == 0


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_cache_invalidated_on_item_save(
    django_capture_on_commit_callbacks,
):
    """Saving an item size should invalidate the creator's cached usage."""
    client = APIClient()
    user = factories.UserFactory()
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=400)
    client.force_authenticate(user)

    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 400

    item.size = 700
    with django_capture_on_commit_callbacks(execute=True):
        item.save(update_fields=["size"])

    assert cache.get(get_storage_used_cache_key(user.id)) is None
    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 700


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_api_entitlements_local_cache_invalidated_on_quota_excluded(
    django_capture_on_commit_callbacks,
):
    """Flagging an item as quota excluded should invalidate the creator's cached usage."""
    client = APIClient()
    user = factories.UserFactory()
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=400)
    client.force_authenticate(user)

    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 400

    item.quota_excluded = True
    with django_capture_on_commit_callbacks(execute=True):
        item.save(update_fields=["quota_excluded"])

    assert cache.get(get_storage_used_cache_key(user.id)) is None
    response = client.get("/api/v1.0/entitlements/")
    assert response.json()["quota"]["usage"] == 0


def test_api_entitlements_local_cache_invalidated_on_hard_delete(
    django_capture_on_commit_callbacks,
):
    """Hard deleting a folder should invalidate the cache of every descendant creator."""
    owner = factories.UserFactory()
    other = factories.UserFactory()
    folder = factories.ItemFactory(creator=owner, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, parent=folder, creator=owner, size=100)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, parent=folder, creator=other, size=200)

    cache.set(get_storage_used_cache_key(owner.id), 100)
    cache.set(get_storage_used_cache_key(other.id), 200)

    folder.soft_delete()
    with django_capture_on_commit_callbacks(execute=True):
        folder.hard_delete()

    assert cache.get(get_storage_used_cache_key(owner.id)) is None
    assert cache.get(get_storage_used_cache_key(other.id)) is None


def test_api_entitlements_local_cache_invalidated_on_move_to_root(
    django_capture_on_commit_callbacks,
):
    """Moving an item to the root should invalidate the previous creator's cache."""
    creator = factories.UserFactory()
    mover = factories.UserFactory()
    client = APIClient()
    client.force_login(mover)

    folder = factories.ItemFactory(
        creator=creator,
        users=[(creator, models.RoleChoices.OWNER), (mover, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(creator=creator, parent=folder, type=models.ItemTypeChoices.FOLDER)

    cache.set(get_storage_used_cache_key(creator.id), 123)
    cache.set(get_storage_used_cache_key(mover.id), 456)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(f"/api/v1.0/items/{item.id!s}/move/", data={})
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.creator == mover
    assert cache.get(get_storage_used_cache_key(creator.id)) is None
    assert cache.get(get_storage_used_cache_key(mover.id)) is None


def test_api_entitlements_local_cache_invalidated_on_reconciliation(
    django_capture_on_commit_callbacks,
):
    """Reconciling two accounts should invalidate both users' cached usage."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=inactive, size=300)

    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email,
        inactive_email=inactive.email,
        active_email_checked=True,
        inactive_email_checked=True,
    )

    cache.set(get_storage_used_cache_key(active.id), 0)
    cache.set(get_storage_used_cache_key(inactive.id), 300)

    with django_capture_on_commit_callbacks(execute=True):
        reconciliation.process_reconciliation_request()

    assert cache.get(get_storage_used_cache_key(active.id)) is None
    assert cache.get(get_storage_used_cache_key(inactive.id)) is None
