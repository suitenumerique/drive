import importlib

from django.urls import clear_url_caches


def reload_urls():
    """Reload the URLs to test the external API URLs."""
    import core.urls  # pylint:disable=import-outside-toplevel # noqa: PLC0415

    import drive.urls  # pylint:disable=import-outside-toplevel # noqa: PLC0415

    importlib.reload(core.urls)  # Add this line
    importlib.reload(drive.urls)
    clear_url_caches()
