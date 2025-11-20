"""
Storage compute backend utilities.
"""

import functools

from django.conf import settings
from django.utils.module_loading import import_string


@functools.cache
def get_storage_compute_backend():
    """
    Get the storage compute backend.
    """
    backend = import_string(settings.STORAGE_COMPUTE_BACKEND)()
    return backend
