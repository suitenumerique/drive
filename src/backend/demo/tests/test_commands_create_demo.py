"""Test the `create_demo` management command"""

from django.core.management import call_command
from django.test import override_settings

import pytest

from core import models

from demo import defaults
from demo.management.commands.create_demo import FILE_TYPE_ITEMS

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True)
def test_commands_create_demo():
    """The create_demo management command should create objects as expected."""
    call_command("create_demo")

    assert models.User.objects.count() == 5
    assert set(models.User.objects.values_list("email", flat=True)) == {
        user["email"] for user in defaults.USERS
    } | {"drive@drive.world"}
    assert not models.User.objects.filter(full_name__isnull=True).exists()
    assert not models.User.objects.filter(full_name="").exists()
    assert not models.User.objects.filter(short_name__isnull=True).exists()
    assert not models.User.objects.filter(short_name="").exists()
    assert models.Item.objects.count() >= 10
    assert models.ItemAccess.objects.count() > 10

    # assert dev users have doc accesses
    user = models.User.objects.get(email="drive@drive.world")
    assert models.ItemAccess.objects.filter(user=user).exists()


@override_settings(DEBUG=True)
def test_commands_create_demo_with_file_types():
    """The create_demo command should optionally add files for filter development."""
    call_command("create_demo", "--file_types")

    expected_filenames = {item["filename"] for item in FILE_TYPE_ITEMS}
    expected_mimetypes = {item["mimetype"] for item in FILE_TYPE_ITEMS}
    file_type_items = models.Item.objects.filter(filename__in=expected_filenames)

    assert file_type_items.count() == len(FILE_TYPE_ITEMS)
    assert set(file_type_items.values_list("mimetype", flat=True)) == expected_mimetypes
    assert all(item.is_root for item in file_type_items)


@override_settings(DEBUG=True)
def test_commands_create_demo_can_be_run_twice_without_resetting_database():
    """The create_demo command should reuse deterministic demo users."""
    call_command("create_demo", "--file_types")
    call_command("create_demo", "--file_types")

    assert models.User.objects.filter(email="drive@drive.world").count() == 1
