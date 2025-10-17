"""Utils for testing URLs."""

import importlib

from django.urls import clear_url_caches


def reload_urls():
    """
    Reload the URLs. Since the url are loaded based on a
    settings value, we need to reload the urls to make the
    URL settings based condition effective.
    """
    import core.urls  # pylint:disable=import-outside-toplevel # noqa: PLC0415

    import drive.urls  # pylint:disable=import-outside-toplevel # noqa: PLC0415

    importlib.reload(core.urls)
    importlib.reload(drive.urls)
    clear_url_caches()
