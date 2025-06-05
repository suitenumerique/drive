"""Tests for the wopi utils."""

from urllib.parse import quote_plus

from django.core.cache import cache

import pytest

from core import models
from core.factories import ItemFactory
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY
from wopi.utils import (
    compute_wopi_launch_url,
    get_wopi_client_config,
    is_item_wopi_supported,
)

pytestmark = pytest.mark.django_db


def test_is_item_wopi_supported():
    """Test the is_item_wopi_supported function."""

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "https://vendorA.com/launch_url",
            },
            "extensions": {
                "docx": "https://vendorA.com/launch_url",
            },
        },
    )
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert is_item_wopi_supported(item)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        mimetype="application/pdf",
        filename="test.pdf",
    )
    assert not is_item_wopi_supported(item)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        filename="test.docx",
    )

    assert is_item_wopi_supported(item)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        filename="test",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert is_item_wopi_supported(item)

    item = ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    assert not is_item_wopi_supported(item)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    assert not is_item_wopi_supported(item)


def test_get_wopi_client_config():
    """Test the get_wopi_client_config function."""

    # pylint: disable=line-too-long
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "https://vendorA.com/launch_url",
            },
            "extensions": {
                "docx": "https://vendorA.com/launch_url",
            },
        },
    )
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="test.docx",
    )
    assert get_wopi_client_config(item) == "https://vendorA.com/launch_url"

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        mimetype="application/pdf",
        filename="test.pdf",
    )
    assert not get_wopi_client_config(item)

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        filename="test.docx",
    )

    assert get_wopi_client_config(item) == "https://vendorA.com/launch_url"

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
        filename="test",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert get_wopi_client_config(item) == "https://vendorA.com/launch_url"

    item = ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    assert get_wopi_client_config(item) is None

    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    assert get_wopi_client_config(item) is None


def test_get_wopi_client_config_no_configuration():
    """Test the get_wopi_client_config function with no configuration."""

    cache.set(WOPI_CONFIGURATION_CACHE_KEY, None)
    item = ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )
    assert get_wopi_client_config(item) is None


def test_compute_wopi_launch_url(settings):
    """Test the compute_wopi_launch_url function."""
    settings.WOPI_SRC_BASE_URL = "http://app-dev:8000"
    launch_url = "https://vendorA.com/launch_url"
    get_file_info_path = "/api/v1.0/wopi/files/123"
    assert (
        compute_wopi_launch_url(launch_url, get_file_info_path)
        == f"{launch_url}?WOPISrc={quote_plus(f'{settings.WOPI_SRC_BASE_URL}{get_file_info_path}')}"
    )

    settings.WOPI_SRC_BASE_URL = None
    assert (
        compute_wopi_launch_url(launch_url, get_file_info_path)
        == f"{launch_url}?WOPISrc={quote_plus(get_file_info_path)}"
    )
