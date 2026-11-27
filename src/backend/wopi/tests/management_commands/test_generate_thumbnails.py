"""Tests for the generate_thumbnails management command."""

from unittest import mock

from django.core.management import CommandError, call_command

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_generate_thumbnails_refreshes_configuration_then_queues_ready_files(settings):
    """The formats each client renders are refreshed before every ready file is queued."""
    settings.WOPI_CLIENTS = ["collabora"]
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "collabora": {"options": {"ThumbnailServiceUrl": "http://collabora/cool/convert-to"}}
    }
    ready = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.ANALYZING,
    )
    calls = mock.Mock()

    with (
        mock.patch(
            "wopi.management.commands.generate_thumbnails.configure_wopi_clients",
            calls.configure,
        ),
        mock.patch(
            "wopi.management.commands.generate_thumbnails.generate_item_thumbnail",
            calls.task,
        ),
    ):
        call_command("generate_thumbnails")

    assert calls.mock_calls == [mock.call.configure(), mock.call.task.delay(str(ready.id))]


def test_generate_thumbnails_without_client_opting_in(settings):
    """The command fails when no client renders thumbnails."""
    settings.WOPI_CLIENTS = ["collabora"]
    settings.WOPI_CLIENTS_CONFIGURATION = {"collabora": {"options": {}}}

    with (
        mock.patch(
            "wopi.management.commands.generate_thumbnails.configure_wopi_clients"
        ) as configure,
        pytest.raises(CommandError),
    ):
        call_command("generate_thumbnails")

    configure.assert_not_called()
