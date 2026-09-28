"""
Test Entitlements API endpoints with DeployCenter entitlements backend.
"""

import json
import urllib.parse
from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.storage import default_storage
from django.test import override_settings

import pytest
import responses
from rest_framework.test import APIClient

from core import factories, models
from core.api.viewsets import malware_detection
from core.entitlements import get_entitlements_backend
from core.entitlements.backends.deploycenter import (
    ENTITLEMENTS_CACHE_KEY_PREFIX,
    DeployCenterEntitlementsBackend,
)

pytestmark = pytest.mark.django_db

ENTITLEMENTS_URL = "http://backend-dev:8000/api/v1.0/entitlements/"
ENTITLEMENTS_BACKEND_PARAMETERS = {
    "base_url": ENTITLEMENTS_URL,
    "api_key": "3e489c7c0029cf448c4d965de0c69ed11706aac46767be6138f44cabe4cf8d42",
    "service_id": 8,
    "oidc_claims": ["siret"],
}


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
def test_api_entitlements_deploycenter_get_entitlements_anonymous():
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
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_both_true():
    """Authenticated users should get entitlements when both can_access and can_upload are True."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "21140001500015"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )
    assert responses.calls[0].request.headers["Content-Type"] == "application/json"
    assert json.loads(responses.calls[0].request.body) == {
        "usage_metrics": [
            {
                "account": {"type": "user", "id": user.sub, "email": user.email},
                "siret": "21140001500015",
                "metrics": {"storage_used": 0},
            },
            {
                "account": {"type": "organization"},
                "siret": "21140001500015",
                "metrics": {"storage_used": 0},
            },
        ],
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_can_upload_false():
    """Authenticated users should get correct entitlements when can_upload is False."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_reason": "not_activated",
            },
            "organization": "ACME",
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": False,
            "reason": "not_activated",
        },
        "context": {
            "organization": "ACME",
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_can_access_false():
    """Authenticated users should get correct entitlements when can_access is False."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": False,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": False,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_cache():
    """Authenticated users should get entitlements from cache when doing subsequent requests."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )

    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    # Verify that the request was not made again.
    assert len(responses.calls) == 1


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_invalidate_cache():
    """Invalidating the cache should force the next read to hit DeployCenter again."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)

    client.get("/api/v1.0/entitlements/")
    client.get("/api/v1.0/entitlements/")
    assert len(responses.calls) == 1

    get_entitlements_backend().invalidate_cache([user.id])
    assert cache.get(f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user.id}") is None

    client.get("/api/v1.0/entitlements/")
    assert len(responses.calls) == 2


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_cache_invalidated_on_upload_ended(
    django_capture_on_commit_callbacks,
):
    """Ending an upload should invalidate the uploader's cached entitlements."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, filename="my_file.txt", creator=user
    )
    factories.UserItemAccessFactory(item=item, user=user, role="owner")
    default_storage.save(item.file_key, BytesIO(b"my prose"))

    with (
        mock.patch.object(malware_detection, "analyse_file"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")
    assert response.status_code == 200

    # The can_upload gate cached pre-upload entitlements during the request:
    # they must be gone once the upload has been committed.
    assert len(responses.calls) == 1
    assert cache.get(f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user.id}") is None

    client.get("/api/v1.0/entitlements/")
    assert len(responses.calls) == 2


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
def test_api_entitlements_deploycenter_cache_invalidated_on_hard_delete(
    django_capture_on_commit_callbacks,
):
    """Hard deleting a folder should invalidate every descendant creator's entitlements."""
    owner = factories.UserFactory()
    other = factories.UserFactory()
    folder = factories.ItemFactory(creator=owner, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, parent=folder, creator=owner, size=100)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, parent=folder, creator=other, size=200)

    cache.set(f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{owner.id}", {"entitlements": {}})
    cache.set(f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{other.id}", {"entitlements": {}})

    folder.soft_delete()
    with django_capture_on_commit_callbacks(execute=True):
        folder.hard_delete()

    assert cache.get(f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{owner.id}") is None
    assert cache.get(f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{other.id}") is None


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
@pytest.mark.parametrize("reason", ["no_organization", "not_activated"])
def test_api_entitlements_deploycenter_quota_hidden(reason):
    """The quota gauge should be hidden when the service is not usable by the user."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_reason": reason,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert "quota" not in response.json()
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": reason,
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_quota_organization_exceeded():
    """The quota gauge should be locked when the organization quota is reached."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_resolve_level": "organization",
                "max_storage_organization": 100000000,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["quota"] == {
        "state": "exceeded_locked",
        "reason": "organization_quota_exceeded",
    }
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "organization_quota_exceeded",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_quota_error_metric_account_not_found():
    """The quota gauge should be in error when the account metrics are missing."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["quota"] == {
        "state": "error",
        "error": "metric_account_not_found",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_quota_error_max_storage_account_not_found():
    """The quota gauge should be in error when the account storage limit is missing."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["quota"] == {
        "state": "error",
        "error": "max_storage_account_not_found",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
@pytest.mark.parametrize(
    "resolve_level,expected_reason",
    [
        ("user", "user_quota_exceeded"),
        ("user_override", "user_override_quota_exceeded"),
        ("organization", "organization_quota_exceeded"),
    ],
)
def test_api_entitlements_deploycenter_can_upload_reason_from_resolve_level(
    resolve_level, expected_reason
):
    """When no explicit reason is given, it should be derived from the resolve level."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_resolve_level": resolve_level,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": expected_reason,
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_can_upload_explicit_reason_wins():
    """An explicit reason should take precedence over the resolve level fallback."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_reason": "not_activated",
                "can_upload_resolve_level": "user",
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "not_activated",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_usage_metrics_organization_aggregation():
    """The organization entry should aggregate active users sharing the same siret."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={"entitlements": {"can_access": True, "can_upload": True}},
        status=200,
    )

    user = factories.UserFactory(claims={"siret": "21140001500015"})
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=700)
    colleague = factories.UserFactory(claims={"siret": "21140001500015"})
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=colleague, size=800)
    stranger = factories.UserFactory(claims={"siret": "99999999999999"})
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=stranger, size=1000)
    former_colleague = factories.UserFactory(claims={"siret": "21140001500015"}, is_active=False)
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=former_colleague, size=1000)

    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert json.loads(responses.calls[0].request.body) == {
        "usage_metrics": [
            {
                "account": {"type": "user", "id": user.sub, "email": user.email},
                "siret": "21140001500015",
                "metrics": {"storage_used": 700},
            },
            {
                "account": {"type": "organization"},
                "siret": "21140001500015",
                "metrics": {"storage_used": 1500},
            },
        ],
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_usage_metrics_no_organization_claim():
    """Without a siret claim, only the user entry should be sent, without a siret."""
    responses.add(
        responses.POST,
        ENTITLEMENTS_URL,
        json={"entitlements": {"can_access": True, "can_upload": True}},
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert "siret" not in responses.calls[0].request.url
    assert json.loads(responses.calls[0].request.body) == {
        "usage_metrics": [
            {
                "account": {"type": "user", "id": user.sub, "email": user.email},
                "metrics": {"storage_used": 0},
            },
        ],
    }


def test_api_entitlements_deploycenter_usage_metrics_custom_organization_claim():
    """A custom organization claim should drive both the lookup and the payload key."""
    backend = DeployCenterEntitlementsBackend(
        base_url=ENTITLEMENTS_URL,
        service_id=8,
        api_key="secret",
        organization_claim="org_id",
    )
    user = factories.UserFactory(claims={"org_id": "acme", "siret": "21140001500015"})
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=user, size=700)
    colleague = factories.UserFactory(claims={"org_id": "acme"})
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, creator=colleague, size=800)

    assert backend.build_usage_metrics(user) == [
        {
            "account": {"type": "user", "id": user.sub, "email": user.email},
            "org_id": "acme",
            "metrics": {"storage_used": 700},
        },
        {
            "account": {"type": "organization"},
            "org_id": "acme",
            "metrics": {"storage_used": 1500},
        },
    ]


def test_api_entitlements_deploycenter_missing_base_url_parameter():
    """Missing base_url parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(  # pylint: disable=no-value-for-parameter
            service_id=8,
            api_key="secret",
        )


def test_api_entitlements_deploycenter_missing_api_key_parameter():
    """Missing api_key parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(  # pylint: disable=no-value-for-parameter
            base_url=ENTITLEMENTS_URL,
            service_id=8,
        )


def test_api_entitlements_deploycenter_missing_service_id_parameter():
    """Missing service_id parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(  # pylint: disable=no-value-for-parameter
            base_url=ENTITLEMENTS_URL,
            api_key="secret",
        )
