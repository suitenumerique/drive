"""Tests for the item admin class."""

from unittest import mock

from django.contrib import admin
from django.test import RequestFactory

import pytest

from core import factories, models
from core.admin import ItemAdmin

pytestmark = pytest.mark.django_db


def test_admin_item_trigger_file_analysis():
    """The action reanalyses the file of each selected file item."""
    file_item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="foo.txt")
    factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    admin_instance = ItemAdmin(models.Item, admin.site)
    request = RequestFactory().post("/")
    request.user = factories.UserFactory(is_staff=True, is_superuser=True)

    with (
        mock.patch("core.admin.reanalyse_file") as mock_reanalyse_file,
        mock.patch.object(admin_instance, "message_user"),
    ):
        admin_instance.trigger_file_analysis(request, models.Item.objects.all())

    mock_reanalyse_file.assert_called_once_with(file_item.file_key, item_id=file_item.id)
