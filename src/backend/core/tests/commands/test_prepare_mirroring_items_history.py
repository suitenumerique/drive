"""Tests for the prepare_mirroring_items_history command."""

import random
from itertools import islice

from django.core.management import call_command

import pytest

from core.factories import ItemFactory, MirrorItemTaskFactory
from core.models import (
    ItemTypeChoices,
    ItemUploadStateChoices,
    MirrorItemTask,
    MirrorItemTaskStatusChoices,
)

pytestmark = pytest.mark.django_db


def test_prepare_mirroring_items_history():
    """Test the prepare_mirroring_items_history command."""

    # Create a batch of items type file with upload state different from PENDING
    items = ItemFactory.create_batch(
        100,
        type=ItemTypeChoices.FILE,
        update_upload_state=random.choice(
            [
                status[0]
                for status in ItemUploadStateChoices.choices
                if status[0] != ItemUploadStateChoices.PENDING
            ]
        ),
    )

    # create a batch of items type file with upload state PENDING
    ItemFactory.create_batch(
        20,
        type=ItemTypeChoices.FILE,
        update_upload_state=ItemUploadStateChoices.PENDING,
    )

    # Create a batch of MirrorItemTask from the items
    number_of_mirror_item_tasks = random.randint(10, 20)
    for item in islice(items, number_of_mirror_item_tasks):
        MirrorItemTaskFactory(
            item=item, status=random.choice(MirrorItemTaskStatusChoices.values)
        )

    # call the command
    call_command("prepare_mirroring_items_history")

    # check that the number of mirror item tasks is equal to the number
    # of items with upload state different from PENDING

    assert MirrorItemTask.objects.count() == 100

    # Check there is no duplicated items in the mirror item tasks
    assert MirrorItemTask.objects.count() == len(
        set(MirrorItemTask.objects.values_list("item_id", flat=True))
    )
