"""Test the `create_demo` management command"""

from unittest import mock

from django.core.management import call_command
from django.test import override_settings

import pytest

from core import models

pytestmark = pytest.mark.django_db


@mock.patch(
    "demo.defaults.NB_OBJECTS",
    {
        "users": 10,
        "files": 10,
        "max_users_per_document": 5,
    },
)
@override_settings(DEBUG=True)
def test_commands_create_demo():
    """The create_demo management command should create objects as expected."""
    call_command("create_demo")

    assert models.User.objects.count() >= 10
    assert models.Item.objects.count() >= 10
    assert models.ItemAccess.objects.count() > 10

    # assert dev users have doc accesses
    user = models.User.objects.get(email="drive@drive.world")
    assert models.ItemAccess.objects.filter(user=user).exists()
