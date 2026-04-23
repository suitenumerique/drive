"""Entitlements backend factory."""

import functools

from django.conf import settings
from django.utils.module_loading import import_string


@functools.cache
def get_entitlements_backend():
    """Get the entitlements backend."""
    return import_string(settings.ENTITLEMENTS_BACKEND)(**settings.ENTITLEMENTS_BACKEND_PARAMETERS)
