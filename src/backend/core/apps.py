"""Drive Core application"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """Configuration class for the drive core app."""

    name = "core"
    app_label = "core"
    verbose_name = _("drive core application")

    def ready(self):
        """
        Import signals when the app is ready.
        """
        # pylint: disable=import-outside-toplevel, unused-import
        from . import signals  # noqa: PLC0415,F401

        # Register the periodic tasks before celery beat finalizes its app
        from .tasks import management_commands  # noqa: PLC0415

        # Celery only logs errors raised in its signal handlers: validate here so a
        # misconfiguration stops the process instead of never running the command.
        management_commands.get_periodic_management_commands()
