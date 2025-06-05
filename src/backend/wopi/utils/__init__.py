"""Utils for WOPI"""

from urllib.parse import quote_plus

from django.conf import settings
from django.core.cache import cache

from core import models
from wopi.tasks.configure_wopi import (
    WOPI_CONFIGURATION_CACHE_KEY,
    WOPI_DEFAULT_CONFIGURATION,
)


def is_item_wopi_supported(item):
    """
    Check if an item is supported by WOPI.
    """
    return bool(get_wopi_client_config(item))


def get_wopi_client_config(item):
    """make
    Get the WOPI client configuration for an item.
    """
    if item.type != models.ItemTypeChoices.FILE:
        return None

    if item.upload_state != models.ItemUploadStateChoices.UPLOADED:
        return None

    wopi_configuration = cache.get(
        WOPI_CONFIGURATION_CACHE_KEY, default=WOPI_DEFAULT_CONFIGURATION
    )

    if not wopi_configuration:
        return None

    if item.extension in wopi_configuration["extensions"]:
        return wopi_configuration["extensions"][item.extension]
    if item.mimetype in wopi_configuration["mimetypes"]:
        return wopi_configuration["mimetypes"][item.mimetype]

    return None


def compute_wopi_launch_url(launch_url, get_file_info_path):
    """
    Compute the WOPI launch URL for an item.
    """
    launch_url = launch_url.rstrip("?")

    wopi_src_base_url = settings.WOPI_SRC_BASE_URL
    wopi_src = get_file_info_path
    if wopi_src_base_url:
        wopi_src = f"{wopi_src_base_url}{get_file_info_path}"
    return f"{launch_url}?WOPISrc={quote_plus(wopi_src)}"
