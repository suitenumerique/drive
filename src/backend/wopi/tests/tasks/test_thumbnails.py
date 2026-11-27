"""Test the thumbnail tasks of the wopi app."""

from unittest import mock

import pytest

from core import factories, models
from wopi.tasks.thumbnails import generate_item_thumbnail, queue_item_thumbnail

pytestmark = pytest.mark.django_db


def test_queue_item_thumbnail_once_until_the_render_starts():
    """Saves before the render starts queue nothing more, saves after it queue a new one."""
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE)

    with (
        mock.patch.object(generate_item_thumbnail, "apply_async") as apply_async,
        mock.patch("wopi.tasks.thumbnails.generate_thumbnail") as generate_thumbnail,
    ):
        queue_item_thumbnail(str(item.id), countdown=120)
        queue_item_thumbnail(str(item.id), countdown=120)
        assert apply_async.call_count == 1

        generate_item_thumbnail(str(item.id))
        generate_thumbnail.assert_called_once_with(item)

        queue_item_thumbnail(str(item.id), countdown=120)
        assert apply_async.call_count == 2


def test_queue_item_thumbnail_per_item():
    """A render queued for one item does not hold back the others."""
    items = factories.ItemFactory.create_batch(2, type=models.ItemTypeChoices.FILE)

    with mock.patch.object(generate_item_thumbnail, "apply_async") as apply_async:
        for item in items:
            queue_item_thumbnail(str(item.id))

    assert apply_async.call_count == 2
