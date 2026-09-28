"""Permissions backend factory."""

import functools

from django.conf import settings
from django.utils.module_loading import import_string


@functools.cache
def get_permissions_backend():
    """Get the permissions backend."""
    return import_string(settings.PERMISSIONS_BACKEND)(**settings.PERMISSIONS_BACKEND_PARAMETERS)
