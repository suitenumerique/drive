"""Tests for the conversion celery tasks."""

from unittest import mock

import pytest
from celery.exceptions import Retry

from core import factories, models
from wopi.conversion import exceptions
from wopi.tasks import conversion

pytestmark = pytest.mark.django_db

# As the task is bound, we need to ignore this error.
# pylint: disable=no-value-for-parameter


def _source_and_placeholder():
    """Build a user with a ready source file and a converting placeholder."""
    user = factories.UserFactory()
    source = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    placeholder = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FILE,
        filename="document.docx",
        update_upload_state=models.ItemUploadStateChoices.CONVERTING,
    )
    return user, source, placeholder


def test_convert_file_calls_perform_conversion():
    """Delegate to perform_conversion with the resolved entities on success."""
    user, source, placeholder = _source_and_placeholder()

    with mock.patch.object(conversion, "perform_conversion") as perform_mock:
        conversion.convert_file(
            source_item_id=str(source.id),
            converted_item_id=str(placeholder.id),
            user_id=str(user.id),
        )

    perform_mock.assert_called_once()
    called_source, called_placeholder, called_user = perform_mock.call_args.args
    assert (called_source.id, called_placeholder.id, called_user.id) == (
        source.id,
        placeholder.id,
        user.id,
    )


def test_convert_file_keeps_placeholder_on_conversion_error():
    """Re-raise ConversionError without touching the placeholder."""
    user, source, placeholder = _source_and_placeholder()

    with mock.patch.object(
        conversion, "perform_conversion", side_effect=exceptions.ConversionError("boom")
    ):
        with pytest.raises(exceptions.ConversionError):
            conversion.convert_file(
                source_item_id=str(source.id),
                converted_item_id=str(placeholder.id),
                user_id=str(user.id),
            )

    placeholder.refresh_from_db()
    assert placeholder.upload_state == models.ItemUploadStateChoices.CONVERTING


def test_convert_file_keeps_placeholder_on_unexpected_exception():
    """Re-raise any uncaught exception without touching the placeholder."""
    user, source, placeholder = _source_and_placeholder()

    with mock.patch.object(
        conversion, "perform_conversion", side_effect=RuntimeError("unexpected")
    ):
        with pytest.raises(RuntimeError):
            conversion.convert_file(
                source_item_id=str(source.id),
                converted_item_id=str(placeholder.id),
                user_id=str(user.id),
            )

    placeholder.refresh_from_db()
    assert placeholder.upload_state == models.ItemUploadStateChoices.CONVERTING


def test_convert_file_aborts_when_placeholder_state_changed():
    """Skip work when the placeholder is no longer CONVERTING."""
    user, source, placeholder = _source_and_placeholder()
    placeholder.upload_state = models.ItemUploadStateChoices.READY
    placeholder.save(update_fields=["upload_state", "updated_at"])

    with mock.patch.object(conversion, "perform_conversion") as perform_mock:
        conversion.convert_file(
            source_item_id=str(source.id),
            converted_item_id=str(placeholder.id),
            user_id=str(user.id),
        )

    perform_mock.assert_not_called()


def test_convert_file_retries_while_source_analyzing():
    """Wait for malware analysis to finish before converting the source bytes."""
    user, source, placeholder = _source_and_placeholder()
    source.upload_state = models.ItemUploadStateChoices.ANALYZING
    source.save(update_fields=["upload_state", "updated_at"])

    with (
        mock.patch.object(conversion.convert_file, "retry", side_effect=Retry()) as retry_mock,
        mock.patch.object(conversion, "perform_conversion") as perform_mock,
    ):
        with pytest.raises(Retry):
            conversion.convert_file(
                source_item_id=str(source.id),
                converted_item_id=str(placeholder.id),
                user_id=str(user.id),
            )

    retry_mock.assert_called_once()
    perform_mock.assert_not_called()


def test_convert_file_ignores_missing_source():
    """Ignore a missing source item without crashing."""
    conversion.convert_file(
        source_item_id="00000000-0000-0000-0000-000000000000",
        converted_item_id="00000000-0000-0000-0000-000000000000",
        user_id="00000000-0000-0000-0000-000000000000",
    )


def test_convert_file_ignores_missing_placeholder():
    """Ignore a missing placeholder without crashing."""
    user, source, _ = _source_and_placeholder()

    conversion.convert_file(
        source_item_id=str(source.id),
        converted_item_id="00000000-0000-0000-0000-000000000000",
        user_id=str(user.id),
    )
