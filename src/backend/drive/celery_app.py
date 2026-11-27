"""Drive celery configuration file."""

import os
from pathlib import Path

from celery import Celery, bootsteps
from configurations.importer import install
from django_structlog.celery.steps import DjangoStructLogInitStep

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drive.settings")
os.environ.setdefault("DJANGO_CONFIGURATION", "Development")

install(check_options=True)

# Can be loaded only after install call.
from django.conf import settings  # pylint: disable=wrong-import-position

# Checked by the probes of the worker containers, see the helm chart
WORKER_HEARTBEAT_FILE = Path("/tmp/celery_worker_heartbeat")  # noqa: S108
WORKER_HEARTBEAT_INTERVAL = 10  # seconds


class WorkerHeartbeatStep(bootsteps.StartStopStep):
    """Touch a file from the worker event loop to show it is alive."""

    requires = {"celery.worker.components:Timer"}

    def __init__(self, parent, **kwargs):
        """Initialize the step without a running timer."""
        super().__init__(parent, **kwargs)
        self.tref = None

    def start(self, parent):
        """Touch the heartbeat file now, then at a fixed interval."""
        WORKER_HEARTBEAT_FILE.touch()
        self.tref = parent.timer.call_repeatedly(
            WORKER_HEARTBEAT_INTERVAL, WORKER_HEARTBEAT_FILE.touch
        )

    def stop(self, parent):
        """Stop the timer and remove the heartbeat file."""
        if self.tref:
            self.tref.cancel()
        WORKER_HEARTBEAT_FILE.unlink(missing_ok=True)


app = Celery("drive")
# Log the tasks with the context of the request that sent them
app.steps["worker"].add(DjangoStructLogInitStep)
app.steps["worker"].add(WorkerHeartbeatStep)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
