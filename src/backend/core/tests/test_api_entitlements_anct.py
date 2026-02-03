"""
Test Entitlements API endpoints with ANCT entitlements backend.
"""

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

import pytest
import responses
from rest_framework.test import APIClient

from core import factories
from core.entitlements.anct_entitlements_backend import ANCTEntitlementsBackend

pytestmark = pytest.mark.django_db

ENTITLEMENTS_URL = "http://backend-dev:8000/api/v1.0/entitlements/"
ENTITLEMENTS_BACKEND_PARAMETERS = {
    "url": ENTITLEMENTS_URL,
    "token": "3e489c7c0029cf448c4d965de0c69ed11706aac46767be6138f44cabe4cf8d42",
    "service_id": 8,
    "cache_timeout": 5,
}


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
def test_api_entitlements_anct_get_entitlements_anonymous():
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
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_anct_get_entitlements_both_true():
    """Authenticated users should get entitlements when both can_access and can_upload are True."""
    # Mock the entitlements endpoint
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
            }
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
        },
    }
    # Verify the request was made with correct parameters
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id={user.sub}" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['token']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_anct_get_entitlements_can_upload_false():
    """Authenticated users should get entitlements when both can_access and can_upload are True."""
    # Mock the entitlements endpoint
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
            }
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
        },
    }
    # Verify the request was made with correct parameters
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id={user.sub}" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['token']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_anct_get_entitlements_can_access_false():
    """Authenticated users should get entitlements when both can_access and can_upload are True."""
    # Mock the entitlements endpoint
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": False,
                "can_upload": True,
            }
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
        },
    }
    # Verify the request was made with correct parameters
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id={user.sub}" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['token']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_anct_get_entitlements_cache():
    """Authenticated users should get entitlements from cache when doing subsequent requests."""
    # Mock the entitlements endpoint
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
            }
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
        },
    }
    # Verify the request was made with correct parameters
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id={user.sub}" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['token']}"
    )

    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
        },
    }
    # Verify that the request was not made again.
    assert len(responses.calls) == 1


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "token": "3e489c7c0029cf448c4d965de0c69ed11706aac46767be6138f44cabe4cf8d42",
        "service_id": 8,
        "cache_timeout": 5,
    },
)
def test_api_entitlements_anct_missing_url_parameter():
    """Missing url parameter should raise an exception."""
    backend = ANCTEntitlementsBackend()

    with pytest.raises(Exception, match="Invalid entitlements backend configuration"):
        backend.get_parameters()


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "url": ENTITLEMENTS_URL,
        "service_id": 8,
        "cache_timeout": 5,
    },
)
def test_api_entitlements_anct_missing_token_parameter():
    """Missing token parameter should raise an exception."""
    backend = ANCTEntitlementsBackend()

    with pytest.raises(
        ImproperlyConfigured, match="Invalid entitlements backend configuration"
    ):
        backend.get_parameters()


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "url": ENTITLEMENTS_URL,
        "token": "3e489c7c0029cf448c4d965de0c69ed11706aac46767be6138f44cabe4cf8d42",
        "cache_timeout": 5,
    },
)
def test_api_entitlements_anct_missing_service_id_parameter():
    """Missing service_id parameter should raise an exception."""
    backend = ANCTEntitlementsBackend()

    with pytest.raises(
        ImproperlyConfigured, match="Invalid entitlements backend configuration"
    ):
        backend.get_parameters()


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.anct_entitlements_backend.ANCTEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS={
        "url": ENTITLEMENTS_URL,
        "token": "3e489c7c0029cf448c4d965de0c69ed11706aac46767be6138f44cabe4cf8d42",
        "service_id": 8,
        "cache_timeout": "invalid",
    },
)
def test_api_entitlements_anct_invalid_cache_timeout_type():
    """Invalid cache_timeout type (string instead of int) should raise an exception."""
    backend = ANCTEntitlementsBackend()

    with pytest.raises(
        ImproperlyConfigured, match="Invalid entitlements backend configuration"
    ):
        backend.get_parameters()
