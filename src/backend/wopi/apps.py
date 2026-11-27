"""Wopi app configuration."""

from django.apps import AppConfig


class WopiConfig(AppConfig):
    """Configuration class for the wopi app."""

    name = "wopi"

    def ready(self):
        """
        Import signals when the app is ready.
        """
        # pylint: disable=import-outside-toplevel, unused-import
        from . import signals  # noqa: PLC0415,F401
