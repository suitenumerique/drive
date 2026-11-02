"""Drive Core application"""

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """Configuration class for the drive core app."""

    name = "core"
    app_label = "core"
    verbose_name = _("drive core application")

    def ready(self):
        """
        Import signals when the app is ready, and record the database pool
        after each request when the metrics are enabled.
        """
        # pylint: disable=import-outside-toplevel, unused-import
        from . import signals  # noqa: PLC0415,F401

        # Register the periodic tasks before celery beat finalizes its app
        from .tasks import management_commands  # noqa: PLC0415

        # Celery only logs errors raised in its signal handlers: validate here so a
        # misconfiguration stops the process instead of never running the command.
        management_commands.get_periodic_management_commands()

        if settings.PROMETHEUS_METRICS_ENABLED:
            from django.core.signals import request_finished  # noqa: PLC0415

            from core.metrics.database import record_database_pool  # noqa: PLC0415

            request_finished.connect(
                record_database_pool, dispatch_uid="core.metrics.database_pool"
            )
