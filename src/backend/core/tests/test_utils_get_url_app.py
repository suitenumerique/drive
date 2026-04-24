"""module testing the utils function get_url_app"""


import pytest

from core.utils import get_url_app

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def reset_get_url_app_cache():
    """reset the get_url_app cache."""
    get_url_app.cache_clear()


@pytest.mark.parametrize(
    "url_app",
    [
        "https://test-example.com",  # Test with URL_APP set
        None,  # Test fallback to Site domain
    ],
)
def test_get_url_app(url_app, settings):
    """test the get_url_app expected output."""
    settings.URL_APP = url_app

    expected_url_app = url_app or "example.com"

    assert get_url_app() == expected_url_app
