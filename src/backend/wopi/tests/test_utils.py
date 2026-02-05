"""Tests for the wopi utils."""

from urllib.parse import quote_plus

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

import pytest

from core import models
from core.factories import ItemFactory, UserFactory
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY
from wopi.utils import (
    compute_wopi_launch_url,
    get_wopi_client_config,
    is_item_wopi_supported,
)

pytestmark = pytest.mark.django_db


def test_is_item_wopi_supported():
    """Test the is_item_wopi_supported function."""
    user = UserFactory()
    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert is_item_wopi_supported(item, user)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="application/pdf",
        filename="test.pdf",
    )
    assert not is_item_wopi_supported(item, user)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="test.docx",
    )

    assert is_item_wopi_supported(item, user)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="test",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert is_item_wopi_supported(item, user)

    item = ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    assert not is_item_wopi_supported(item, user)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    assert not is_item_wopi_supported(item, user)


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_is_item_wopi_supported_not_ready_but_creator(upload_state):
    """
    Test the is_item_wopi_supported function with a not ready item but the creator is the user.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        creator=user,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert is_item_wopi_supported(item, user)


@pytest.mark.parametrize("creator", [True, False])
def test_is_item_wopi_supported_suspicious_item(creator):
    """Test the is_item_wopi_supported function with a suspicious item."""

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
        creator=user if creator else None,
    )
    assert not is_item_wopi_supported(item, user)


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_is_item_wopi_supported_not_ready_but_not_creator(upload_state):
    """
    Test the is_item_wopi_supported function with a not ready item but the creator is not the user.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert not is_item_wopi_supported(item, user)


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_is_item_wopi_supported_not_ready_anonymous_user(upload_state):
    """
    Test the is_item_wopi_supported function with a not ready item but the creator is not the user.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = AnonymousUser()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert not is_item_wopi_supported(item, user)


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_is_item_wopi_supported_not_ready_none_user(upload_state):
    """
    Test the is_item_wopi_supported function with a not ready item but the user is None.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = None
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert not is_item_wopi_supported(item, user)


def test_get_wopi_client_config():
    """Test the get_wopi_client_config function."""

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert get_wopi_client_config(item, user) == {
        "url": "https://vendorA.com/launch_url",
        "client": "vendorA",
    }

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="application/pdf",
        filename="test.pdf",
    )
    assert not get_wopi_client_config(item, user)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="test.docx",
    )

    assert get_wopi_client_config(item, user) == {
        "url": "https://vendorA.com/launch_url",
        "client": "vendorA",
    }

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="test",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert get_wopi_client_config(item, user) == {
        "url": "https://vendorA.com/launch_url",
        "client": "vendorA",
    }

    item = ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    assert get_wopi_client_config(item, user) is None

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    assert get_wopi_client_config(item, user) is None


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_get_wopi_client_config_not_ready_but_creator(upload_state):
    """
    Test the get_wopi_client_config function with a not ready item but the creator is the user.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        creator=user,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert get_wopi_client_config(item, user) == {
        "url": "https://vendorA.com/launch_url",
        "client": "vendorA",
    }


def test_get_wopi_client_config_no_configuration():
    """Test the get_wopi_client_config function with no configuration."""

    cache.set(WOPI_CONFIGURATION_CACHE_KEY, None)
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    assert get_wopi_client_config(item, user) is None


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_get_wopi_client_config_not_ready_but_not_creator(upload_state):
    """
    Test the get_wopi_client_config function with a not ready item but the creator is not the user.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert get_wopi_client_config(item, user) is None


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_get_wopi_client_config_not_ready_anonymous_user(upload_state):
    """
    Test the get_wopi_client_config function with a not ready item but the creator is not the user.
    """

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = AnonymousUser()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert get_wopi_client_config(item, user) is None


@pytest.mark.parametrize(
    "upload_state",
    [
        value
        for value in models.ItemUploadStateChoices.values
        if value
        not in [
            models.ItemUploadStateChoices.READY,
            models.ItemUploadStateChoices.SUSPICIOUS,
        ]
    ],
)
def test_get_wopi_client_config_not_ready_none_user(upload_state):
    """Test the get_wopi_client_config function with a not ready item but the user is None."""

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = None
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert get_wopi_client_config(item, user) is None


@pytest.mark.parametrize("creator", [True, False])
def test_get_wopi_client_config_suspicious_item(creator):
    """Test the get_wopi_client_config function with a suspicious item."""

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {
                "docx": {"url": "https://vendorA.com/launch_url", "client": "vendorA"},
            },
        },
    )
    user = UserFactory()
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
        creator=user if creator else None,
    )
    assert get_wopi_client_config(item, user) is None


def test_compute_wopi_launch_url(settings):
    """Test the compute_wopi_launch_url function."""
    settings.WOPI_SRC_BASE_URL = "http://app-dev:8000"
    launch_url = "https://vendorA.com/launch_url"
    get_file_info_path = "/api/v1.0/wopi/files/123"
    assert compute_wopi_launch_url(launch_url, get_file_info_path) == (
        f"{launch_url}?WOPISrc={quote_plus(f'{settings.WOPI_SRC_BASE_URL}{get_file_info_path}')}"
        "&closebutton=false"
    )

    settings.WOPI_SRC_BASE_URL = None
    assert (
        compute_wopi_launch_url(launch_url, get_file_info_path)
        == f"{launch_url}?WOPISrc={quote_plus(get_file_info_path)}&closebutton=false"
    )


def test_compute_wopi_launch_url_with_lang(settings):
    """Test the compute_wopi_launch_url function."""
    settings.WOPI_SRC_BASE_URL = "http://app-dev:8000"
    launch_url = "https://vendorA.com/launch_url"
    get_file_info_path = "/api/v1.0/wopi/files/123"
    assert compute_wopi_launch_url(launch_url, get_file_info_path, lang="en-us") == (
        f"{launch_url}?WOPISrc={quote_plus(f'{settings.WOPI_SRC_BASE_URL}{get_file_info_path}')}"
        "&closebutton=false&lang=en-us"
    )

    settings.WOPI_SRC_BASE_URL = None
    assert (
        compute_wopi_launch_url(launch_url, get_file_info_path, lang="en-us")
        == f"{launch_url}?WOPISrc={quote_plus(get_file_info_path)}&closebutton=false&lang=en-us"
    )


def test_compute_wopi_launch_url_leading_question_mark(settings):
    """Test the compute_wopi_launch_url function with a leading question mark."""

    settings.WOPI_SRC_BASE_URL = "http://app-dev:8000"
    launch_url = "https://vendorA.com/launch_url?"
    expected_launch_url = "https://vendorA.com/launch_url"
    get_file_info_path = "/api/v1.0/wopi/files/123"
    assert compute_wopi_launch_url(launch_url, get_file_info_path) == (
        f"{expected_launch_url}?"
        f"WOPISrc={quote_plus(f'{settings.WOPI_SRC_BASE_URL}{get_file_info_path}')}"
        "&closebutton=false"
    )

    settings.WOPI_SRC_BASE_URL = None
    assert (
        compute_wopi_launch_url(launch_url, get_file_info_path)
        == f"{expected_launch_url}?WOPISrc={quote_plus(get_file_info_path)}&closebutton=false"
    )


def test_compute_wopi_launch_url_leading_ampersand(settings):
    """Test the compute_wopi_launch_url function with a leading &."""

    settings.WOPI_SRC_BASE_URL = "http://app-dev:8000"
    launch_url = "https://vendorA.com/launch_url&"
    expected_launch_url = "https://vendorA.com/launch_url"
    get_file_info_path = "/api/v1.0/wopi/files/123"
    assert compute_wopi_launch_url(launch_url, get_file_info_path) == (
        f"{expected_launch_url}?"
        f"WOPISrc={quote_plus(f'{settings.WOPI_SRC_BASE_URL}{get_file_info_path}')}"
        "&closebutton=false"
    )

    settings.WOPI_SRC_BASE_URL = None
    assert (
        compute_wopi_launch_url(launch_url, get_file_info_path)
        == f"{expected_launch_url}?WOPISrc={quote_plus(get_file_info_path)}&closebutton=false"
    )


def test_compute_wopi_launch_url_placeholders(settings):
    """Test the compute_wopi_launch_url function with a leading &."""

    settings.WOPI_SRC_BASE_URL = "http://app-dev:8000"
    launch_url = (
        "http://localhost:9981/hosting/wopi/word/view?"
        "<rs=DC_LLCC&><dchat=DISABLE_CHAT&><embed=EMBEDDED&><fs=FULLSCREEN&><hid=HOST_SESSION_ID&>"
        "<rec=RECORDING&><sc=SESSION_CONTEXT&><thm=THEME_ID&><ui=UI_LLCC&><wopisrc=WOPI_SOURCE&>&"
    )
    get_file_info_path = "/api/v1.0/wopi/files/123"
    expected_launch_url = "http://localhost:9981/hosting/wopi/word/view"
    assert compute_wopi_launch_url(launch_url, get_file_info_path, "en-us") == (
        f"{expected_launch_url}?"
        f"WOPISrc={quote_plus(f'{settings.WOPI_SRC_BASE_URL}{get_file_info_path}')}"
        "&closebutton=false&lang=en-us&rs=en-us&dchat=0&ui=en-us"
    )

    settings.WOPI_SRC_BASE_URL = None
    settings.WOPI_DISABLE_CHAT = 1
    assert compute_wopi_launch_url(launch_url, get_file_info_path) == (
        f"{expected_launch_url}?WOPISrc={quote_plus(get_file_info_path)}"
        "&closebutton=false&dchat=1"
    )
