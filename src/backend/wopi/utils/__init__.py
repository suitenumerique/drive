"""Utils for WOPI"""

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
    """
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
