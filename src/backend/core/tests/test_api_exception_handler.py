"""
Tests for the exception handler of drive's core API.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories
from core.models import ItemTypeChoices

pytestmark = pytest.mark.django_db


def test_api_exception_handler_log(console_logs):
    """API errors should be logged with their status and path."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    console_logs.clear()

    response = client.post("/api/v1.0/items/", {"type": ItemTypeChoices.FILE}, format="json")

    assert response.status_code == 400
    log = console_logs[-1]
    assert log["Type"] == "django.request"
    assert log["Level"] == "WARNING"
    assert log["Fields"] == {
        "msg": "Bad Request: /api/v1.0/items/",
        "request": "<WSGIRequest: POST '/api/v1.0/items/'>",
        "rid": mock.ANY,
        "status_code": 400,
    }
