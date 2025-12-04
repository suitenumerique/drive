"""Test the update_suspicious_item_file_hash command"""

import random
from unittest import mock

from django.core.management import call_command

import pytest

from core import factories, models
from core.management.commands.update_suspicious_item_file_hash import (
    update_suspicious_item_file_hash,
)

pytestmark = pytest.mark.django_db


def test_update_suspicious_item_file_hash_no_items():
    """
    Test the command when there are no items to update.
    """
    with mock.patch.object(
        update_suspicious_item_file_hash, "delay"
    ) as update_suspicious_item_file_hash_mock:
        call_command("update_suspicious_item_file_hash")
        update_suspicious_item_file_hash_mock.assert_not_called()


def test_update_suspicious_item_file_hash_items():
    """
    Test the command when there are items to update.
    """
    not_suspicious_states = [
        choice
        for choice in models.ItemUploadStateChoices.values
        if choice != models.ItemUploadStateChoices.SUSPICIOUS
    ]
    factories.ItemFactory.create_batch(
        3,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=random.choice(not_suspicious_states),
    )
    factories.ItemFactory.create_batch(
        3,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        malware_detection_info={"file_hash": "foo"},
    )
    to_update_items = factories.ItemFactory.create_batch(
        3,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        malware_detection_info={},
    )

    with mock.patch.object(
        update_suspicious_item_file_hash, "delay"
    ) as update_suspicious_item_file_hash_mock:
        call_command("update_suspicious_item_file_hash")

    update_suspicious_item_file_hash_mock.assert_has_calls(
        [mock.call(item.id) for item in to_update_items]
    )
