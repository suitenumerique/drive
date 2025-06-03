"""Tests for the trigger_wopi_configuration management command."""

from unittest import mock

from django.core.management import call_command

from wopi.tasks.configure_wopi import configure_wopi_clients


def test_trigger_wopi_configuration():
    """Test the trigger_wopi_configuration management command."""
    with mock.patch.object(configure_wopi_clients, "delay") as mock_delay:
        call_command("trigger_wopi_configuration")
        mock_delay.assert_called_once()
