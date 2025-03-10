"""Utils for WOPI"""

from django.conf import settings

from core import models


def is_item_wopi_supported(item):
    """
    Check if an item is supported by WOPI.
    """
    if item.type != models.ItemTypeChoices.FILE:
        return False

    if item.upload_state != models.ItemUploadStateChoices.UPLOADED:
        return False

    for _, client_config in settings.WOPI_CLIENTS_CONFIGURATION.items():
        if item.mimetype in client_config["mimetypes"]:
            return True
    return False
