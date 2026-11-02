# Gunicorn-django settings
import os
import tempfile

bind = ["0.0.0.0:8000"]
name = "drive"
python_path = "/app"

# Run
graceful_timeout = 90
timeout = 90
workers = 3

# Logging
# Using '-' for the access log file makes gunicorn log accesses to stdout
accesslog = "-"
# Using '-' for the error log file makes gunicorn log errors to stderr
errorlog = "-"
loglevel = "info"


# Prometheus metrics (PROMETHEUS_METRICS_ENABLED)
# The workers write their numbers to a directory shared by the processes of this
# host. The settings create it inside each worker; the master only has to find it.
def _prometheus_multiproc_dir():
    return os.environ.get("PROMETHEUS_MULTIPROC_DIR") or os.path.join(
        tempfile.gettempdir(), f"drive-prometheus-{os.getuid()}"
    )


def on_starting(server):
    """Drop what a previous run left behind: a reused pid would add to its totals."""
    directory = _prometheus_multiproc_dir()
    if not os.path.isdir(directory) or os.path.islink(directory):
        return
    for name in os.listdir(directory):
        if name.endswith(".db"):
            os.remove(os.path.join(directory, name))


def child_exit(server, worker):
    """Drop the live gauges of a worker that is gone, keep its counters."""
    directory = _prometheus_multiproc_dir()
    if not os.path.isdir(directory):
        return
    # pylint: disable-next=import-outside-toplevel
    from prometheus_client import multiprocess  # noqa: PLC0415

    multiprocess.mark_process_dead(worker.pid, directory)
