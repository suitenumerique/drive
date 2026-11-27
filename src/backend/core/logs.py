"""Log formatting shared by the Django settings and the gunicorn configuration."""

import contextvars
import re

import structlog

# Not a structlog context variable: django-structlog clears those when the view
# returns, before gunicorn has sent the response and logged its errors
gunicorn_request_id = contextvars.ContextVar("gunicorn_request_id", default=None)


def add_gunicorn_request_id(_logger, _method_name, event_dict):
    """Add the id of the request the gunicorn worker handles."""
    request_id = gunicorn_request_id.get()
    if request_id:
        event_dict.setdefault("request_id", request_id)
    return event_dict


def drop_celery_task_data(_logger, _method_name, event_dict):
    """Drop the task context that Celery adds to its logs, whose arguments can hold user data."""
    if event_dict["_record"].name.startswith("celery."):
        event_dict.pop("data", None)
    return event_dict


def redact_access_token(_logger, _method_name, event_dict):
    """Hide the access token that WOPI clients send in the query string of the requests."""
    # "request" for django-structlog, "event" for the gunicorn access log
    for key in ("request", "event"):
        if isinstance(event_dict.get(key), str):
            event_dict[key] = re.sub(r"(access_token=)[^&\s]*", r"\1[redacted]", event_dict[key])
    return event_dict


JSON_FORMATTER = {
    "()": structlog.stdlib.ProcessorFormatter,
    "foreign_pre_chain": [
        structlog.contextvars.merge_contextvars,
        add_gunicorn_request_id,
        structlog.stdlib.ExtraAdder(),
        drop_celery_task_data,
        redact_access_token,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ],
    "processors": [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(default=str),
    ],
}
