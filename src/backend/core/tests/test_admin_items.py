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


def _create_tree(quota_excluded=False):
    """Create a folder with a subfolder and a file created by two users."""
    alice, bob = factories.UserFactory.create_batch(2)
    folder = factories.ItemFactory(
        creator=alice, type=models.ItemTypeChoices.FOLDER, quota_excluded=quota_excluded
    )
    subfolder = factories.ItemFactory(
        creator=bob,
        parent=folder,
        type=models.ItemTypeChoices.FOLDER,
        quota_excluded=quota_excluded,
    )
    file = factories.ItemFactory(
        creator=alice,
        parent=subfolder,
        type=models.ItemTypeChoices.FILE,
        quota_excluded=quota_excluded,
    )
    return folder, [folder, subfolder, file], [alice, bob]


def test_admin_items_exclude_from_quota():
    """The action excludes a folder and all its descendants from the storage quota."""
    folder, tree, users = _create_tree()
    outside = factories.ItemFactory(creator=users[0])
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    queryset = models.Item.objects.filter(pk=folder.pk)
    with mock.patch.object(ItemAdmin, "message_user") as message_user:
        admin_instance.exclude_from_quota(request, queryset)

    for item in tree:
        item.refresh_from_db()
        assert item.quota_excluded is True
    outside.refresh_from_db()
    assert outside.quota_excluded is False
    message_user.assert_called_once_with(request, "3 items updated.")


def test_admin_items_include_in_quota():
    """The action counts a folder and all its descendants in the storage quota again."""
    folder, tree, _users = _create_tree(quota_excluded=True)
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    queryset = models.Item.objects.filter(pk=folder.pk)
    with mock.patch.object(ItemAdmin, "message_user") as message_user:
        admin_instance.include_in_quota(request, queryset)

    for item in tree:
        item.refresh_from_db()
        assert item.quota_excluded is False
    message_user.assert_called_once_with(request, "3 items updated.")


def test_admin_items_exclude_from_quota_file():
    """The action on a file excludes only this file from the storage quota."""
    folder, tree, _users = _create_tree()
    file = tree[-1]
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    queryset = models.Item.objects.filter(pk=file.pk)
    with mock.patch.object(ItemAdmin, "message_user") as message_user:
        admin_instance.exclude_from_quota(request, queryset)

    file.refresh_from_db()
    folder.refresh_from_db()
    assert file.quota_excluded is True
    assert folder.quota_excluded is False
    message_user.assert_called_once_with(request, "1 items updated.")


def test_admin_items_save_model_propagates_quota_excluded():
    """Changing the quota exclusion of a folder should apply it to its descendants."""
    folder, tree, _users = _create_tree()
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    folder.quota_excluded = True
    admin_instance.save_model(request, folder, mock.Mock(changed_data=["quota_excluded"]), True)

    for item in tree:
        item.refresh_from_db()
        assert item.quota_excluded is True


def test_admin_items_save_model_keeps_descendants_quota_excluded():
    """Saving a folder without changing its quota exclusion should not touch its descendants."""
    folder, tree, _users = _create_tree()
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")

    folder.title = "new title"
    models.Item.objects.filter(pk=folder.pk).update(quota_excluded=True)
    folder.quota_excluded = True
    admin_instance.save_model(request, folder, mock.Mock(changed_data=["title"]), True)

    for item in tree[1:]:
        item.refresh_from_db()
        assert item.quota_excluded is False
