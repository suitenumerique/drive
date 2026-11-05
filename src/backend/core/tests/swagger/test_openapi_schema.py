"""
Test suite for generated openapi schema.
"""

import json
import os
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.test import Client, override_settings

import pytest
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import OpenApiJsonRenderer

from core import urls as core_urls
from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db

SCHEMAS_DIR = Path(__file__).parent
EXTERNAL_API_ROUTES = ["items", "item_access", "item_invitation", "users"]


@contextmanager
def _urls_under_settings(**overrides):
    """Reload the urls under the given settings, then restore them."""
    try:
        with override_settings(**overrides):
            reload_urls()
            yield
    finally:
        reload_urls()


def _check_schema(file_name, patterns):
    """Compare the schema of the url patterns to its committed file, or update it on demand."""
    generator = SchemaGenerator(patterns=patterns, api_version=settings.API_VERSION)
    schema = generator.get_schema(request=None, public=True)
    content = OpenApiJsonRenderer().render(schema, renderer_context={}).decode()

    schema_file = SCHEMAS_DIR / file_name
    if os.environ.get("UPDATE_OPENAPI_SCHEMA"):
        schema_file.write_text(content, encoding="utf-8")

    expected_schema = json.loads(schema_file.read_text(encoding="utf-8"))
    assert json.loads(content) == expected_schema, (
        f"{file_name} is out of date, run bin/update_openapi_schema and commit the result."
    )
    return expected_schema


def test_openapi_client_schema():
    """
    Generated and served OpenAPI client schema should match the committed file.
    """
    with _urls_under_settings(OIDC_RESOURCE_SERVER_ENABLED=False, METRICS_ENABLED=False):
        expected_schema = _check_schema("swagger.json", core_urls.urlpatterns)

        response = Client().get("/api/v1.0/swagger.json")

    assert response.status_code == 200
    assert response.json() == expected_schema


def test_openapi_external_api_schema():
    """
    Generated OpenAPI external API schema, with all its routes enabled, should match
    the committed file.
    """
    with _urls_under_settings(
        OIDC_RESOURCE_SERVER_ENABLED=True,
        METRICS_ENABLED=False,
        EXTERNAL_API={route: {"enabled": True, "actions": []} for route in EXTERNAL_API_ROUTES},
    ):
        _check_schema(
            "swagger_external_api.json",
            [
                pattern
                for pattern in core_urls.urlpatterns
                if str(pattern.pattern).startswith("external_api/")
            ],
        )
