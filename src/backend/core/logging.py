"""Logging helpers for the drive core application."""

from uuid import UUID

from dockerflow.logging import MozlogFormatter


class JsonFormatter(MozlogFormatter):
    """Format the logs as MozLog JSON, with the level name for Grafana."""

    def convert_record(self, record):
        """Add the level name next to the numeric syslog severity, and write UUIDs as text."""
        out = super().convert_record(record)
        out["Level"] = record.levelname
        # The JSON encoder of dockerflow writes the repr of the types it does not know
        out["Fields"] = {
            key: str(value) if isinstance(value, UUID) else value
            for key, value in out["Fields"].items()
        }
        return out
