"""Log formatting shared by the Django settings and the gunicorn configuration."""

import re

import structlog


def drop_celery_task_data(_logger, _method_name, event_dict):
    """Drop the task context that Celery adds to its logs, whose arguments can hold user data."""
    if event_dict["_record"].name.startswith("celery."):
        event_dict.pop("data", None)
    return event_dict


def redact_access_token(_logger, _method_name, event_dict):
    """Hide the access token that WOPI clients send in the query string of the requests."""
    if isinstance(event_dict.get("request"), str):
        event_dict["request"] = re.sub(
            r"(access_token=)[^&\s]*", r"\1[redacted]", event_dict["request"]
        )
    return event_dict


JSON_FORMATTER = {
    "()": structlog.stdlib.ProcessorFormatter,
    "foreign_pre_chain": [
        structlog.contextvars.merge_contextvars,
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
