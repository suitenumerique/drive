"""Tests for the item admin class."""

from unittest import mock

from django.contrib import admin
from django.test import RequestFactory

import pytest
from lasuite.malware_detection.models import MalwareDetection, MalwareDetectionStatus

from core import factories, models
from core.admin import ItemAdmin

pytestmark = pytest.mark.django_db


def _create_analyzing_item():
    """Create a file item stuck in the analyzing state with its detection record."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="foo.txt",
        update_upload_state=models.ItemUploadStateChoices.ANALYZING,
    )
    MalwareDetection.objects.create(
        path=item.file_key,
        status=MalwareDetectionStatus.PROCESSING,
        parameters={"item_id": str(item.id)},
    )
    return item


def test_admin_items_mark_items_ready():
    """The action marks selected file items as ready and drops their detections."""
    item = _create_analyzing_item()
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    queryset = models.Item.objects.filter(pk__in=[item.pk, folder.pk])
    with mock.patch.object(ItemAdmin, "message_user") as message_user:
        admin_instance.mark_items_ready(request, queryset)

    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert not MalwareDetection.objects.exists()
    message_user.assert_called_once_with(request, "1 items marked as ready, 1 detections deleted.")


def test_admin_items_mark_items_file_too_large():
    """The action marks selected file items as too large to analyze."""
    item = _create_analyzing_item()
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    queryset = models.Item.objects.filter(pk=item.pk)
    with mock.patch.object(ItemAdmin, "message_user") as message_user:
        admin_instance.mark_items_file_too_large(request, queryset)

    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE
    assert not MalwareDetection.objects.exists()
    message_user.assert_called_once_with(
        request, "1 items marked as file_too_large_to_analyze, 1 detections deleted."
    )
