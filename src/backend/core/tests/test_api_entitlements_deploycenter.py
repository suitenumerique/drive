"""
Test Entitlements API endpoints with DeployCenter entitlements backend.
"""

import urllib.parse

from django.test import override_settings

import pytest
import responses
from rest_framework.test import APIClient

from core import factories
from core.entitlements.backends.deploycenter import DeployCenterEntitlementsBackend

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
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id_value={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_id_key=email" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_can_upload_false():
    """Authenticated users should get correct entitlements when can_upload is False."""
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
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id_value={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_id_key=email" in responses.calls[0].request.url
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
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id_value={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_id_key=email" in responses.calls[0].request.url
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
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_id_value={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_id_key=email" in responses.calls[0].request.url
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
        },
    }
    # Verify that the request was not made again.
    assert len(responses.calls) == 1


def test_api_entitlements_deploycenter_missing_base_url_parameter():
    """Missing base_url parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(
            service_id=8,
            api_key="secret",
        )


def test_api_entitlements_deploycenter_missing_api_key_parameter():
    """Missing api_key parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(
            base_url=ENTITLEMENTS_URL,
            service_id=8,
        )


def test_api_entitlements_deploycenter_missing_service_id_parameter():
    """Missing service_id parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(
            base_url=ENTITLEMENTS_URL,
            api_key="secret",
        )
