# Gunicorn-django settings
import os
import tempfile

from core.logs import JSON_FORMATTER, gunicorn_request_id

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
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
# Using '-' for the error log file makes gunicorn log errors to stderr
errorlog = "-"
loglevel = "info"

# Write gunicorn's logs as JSON, like the application logs. The handler names
# override gunicorn's default ones, which its root logger refers to.
logconfig_dict = {
    "formatters": {"json": JSON_FORMATTER},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "gunicorn.error": {"handlers": ["error_console"], "propagate": False},
        "gunicorn.access": {"handlers": ["console"], "propagate": False},
    },
}


def pre_request(worker, req):
    """Keep the request id for the logs gunicorn writes about the request."""
    worker.log.debug("%s %s", req.method, req.path)
    # Nothing resets it after the request: no hook runs after the error logs
    gunicorn_request_id.set(
        next((value for name, value in req.headers if name == "X-REQUEST-ID"), None)
    )


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
