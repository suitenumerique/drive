"""Tests for the logging configuration."""

import logging


def test_logging_core_logger(console_logs):
    """Logs of the core application should be written to the console."""
    logging.getLogger("core.api").warning("item creation refused")

    assert len(console_logs) == 2
    assert console_logs[0].endswith(" core.api WARNING item creation refused")
    assert console_logs[1].endswith(" core.api WARNING item creation refused")
