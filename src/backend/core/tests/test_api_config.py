"""
Test config API endpoints in the drive core app.
"""

from django.test import override_settings

import pytest
from rest_framework.status import (
    HTTP_200_OK,
)
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


@override_settings(
    CRISP_WEBSITE_ID="123",
    FRONTEND_THEME="test-theme",
    FRONTEND_MORE_LINK="https://test.com",
    FRONTEND_FEEDBACK_BUTTON_SHOW=True,
    FRONTEND_FEEDBACK_BUTTON_IDLE=False,
    FRONTEND_FEEDBACK_ITEMS={"form": {"url": "https://test.com"}},
    FRONTEND_HIDE_GAUFRE=True,
    MEDIA_BASE_URL="http://testserver/",
    POSTHOG_KEY="132456",
    POSTHOG_HOST="https://eu.i.posthog-test.com",
    SENTRY_DSN="https://sentry.test/123",
)
@pytest.mark.parametrize("is_authenticated", [False, True])
def test_api_config(is_authenticated):
    """Anonymous users should be allowed to get the configuration."""
    client = APIClient()

    if is_authenticated:
        user = factories.UserFactory()
        client.force_login(user)

    response = client.get("/api/v1.0/config/")
    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "CRISP_WEBSITE_ID": "123",
        "ENVIRONMENT": "test",
        "FRONTEND_THEME": "test-theme",
        "FRONTEND_MORE_LINK": "https://test.com",
        "FRONTEND_FEEDBACK_BUTTON_SHOW": True,
        "FRONTEND_FEEDBACK_BUTTON_IDLE": False,
        "FRONTEND_FEEDBACK_ITEMS": {"form": {"url": "https://test.com"}},
        "FRONTEND_HIDE_GAUFRE": True,
        "LANGUAGES": [["en-us", "English"], ["fr-fr", "French"], ["de-de", "German"]],
        "LANGUAGE_CODE": "en-us",
        "MEDIA_BASE_URL": "http://testserver/",
        "POSTHOG_KEY": "132456",
        "POSTHOG_HOST": "https://eu.i.posthog-test.com",
        "SENTRY_DSN": "https://sentry.test/123",
    }
