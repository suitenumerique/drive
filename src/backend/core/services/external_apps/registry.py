"""External app backend registry."""

import functools

from django.conf import settings
from django.utils.module_loading import import_string


@functools.cache
def get_external_app_backend(name):
    """
    Return the configured backend for an external app name, or None when the
    app is not declared in settings.EXTERNAL_APPS.
    """
    config = settings.EXTERNAL_APPS.get(name)
    if not config:
        return None

    kwargs = {key: value for key, value in config.items() if key != "backend"}
    return import_string(config["backend"])(name=name, **kwargs)
