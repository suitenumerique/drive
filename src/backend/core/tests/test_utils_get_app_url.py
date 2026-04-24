"""module testing the utils function get_app_url"""

from unittest import mock

import pytest

from core.utils import get_app_url

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "app_url,expected",
    [
        ("https://test-example.com", "https://test-example.com"),
        (None, "example.com"),
    ],
)
def test_get_app_url(app_url, expected, settings):
    """test the get_app_url expected output."""
    settings.APP_URL = app_url

    assert get_app_url() == expected


def test_get_app_url_is_cached(settings):
    """The utility caches its result across successive calls."""
    settings.APP_URL = "https://first.example.com"
    assert get_app_url() == "https://first.example.com"

    with mock.patch("django.contrib.sites.models.Site.objects.get_current") as get_current:
        settings.APP_URL = None
        assert get_app_url() == "https://first.example.com"
        get_current.assert_not_called()
