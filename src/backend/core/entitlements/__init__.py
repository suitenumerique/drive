"""
Entitlements backend utilities.
"""

import functools

from django.conf import settings
from django.utils.module_loading import import_string


@functools.cache
def get_entitlements_backend():
    """
    Get the entitlements backend.
    """
    backend = import_string(settings.ENTITLEMENTS_BACKEND)()
    return backend
