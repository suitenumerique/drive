"""Test the `create_perf_dataset` management command"""

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.models import Count
from django.test import override_settings

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db

SMALL_DATASET = [
    "--users=30",
    "--items=500",
    "--accesses=60",
    "--link-traces=10",
    "--max-favorites-per-user=3",
    "--deleted-ratio=0.1",
]


def get_item_index_names():
    """Return the names of the indexes on the item table."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'drive_item'")
        return {row[0] for row in cursor.fetchall()}


@override_settings(DEBUG=True)
def test_commands_create_perf_dataset():
    """The command should create a consistent dataset of the requested size."""
    index_names = get_item_index_names()

    call_command("create_perf_dataset", *SMALL_DATASET)

    # 30 generated users and the development user
    assert models.User.objects.count() == 31
    # Children counts are random, the item count is approximate
    assert 200 <= models.Item.objects.count() <= 700
    assert models.Item.objects.filter(path__depth=1).count() >= 42
    assert models.ItemAccess.objects.count() <= 63
    assert models.ItemAccess.objects.filter(role=models.RoleChoices.OWNER).count() >= 42
    assert models.LinkTrace.objects.count() <= 11
    assert models.ItemFavorite.objects.exists()

    # Every item has an existing parent
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*) FROM drive_item child
            WHERE nlevel(child.path) > 1 AND NOT EXISTS (
                SELECT 1 FROM drive_item parent
                WHERE parent.path = subpath(child.path, 0, nlevel(child.path) - 1)
            )
            """
        )
        assert cursor.fetchone()[0] == 0

    # Only folders have children, and they belong to the creator of their root
    for item in models.Item.objects.filter(path__depth__gt=1)[:50]:
        parent = item.parent()
        assert parent.type == models.ItemTypeChoices.FOLDER
        assert parent.creator_id == item.creator_id

    # Files are ready, folders have no upload state nor filename
    assert not models.Item.objects.filter(
        type=models.ItemTypeChoices.FILE, filename__isnull=True
    ).exists()
    assert not models.Item.objects.filter(
        type=models.ItemTypeChoices.FOLDER, filename__isnull=False
    ).exists()
    assert set(
        models.Item.objects.filter(type=models.ItemTypeChoices.FILE).values_list(
            "upload_state", flat=True
        )
    ) == {models.ItemUploadStateChoices.READY}

    # Only files are trashed and trashed items are consistent
    trashed = models.Item.objects.filter(deleted_at__isnull=False)
    assert not trashed.exclude(type=models.ItemTypeChoices.FILE).exists()

    # No user gets more favorites than the maximum
    assert (
        max(
            models.ItemFavorite.objects.values("user")
            .annotate(nb=Count("id"))
            .values_list("nb", flat=True)
        )
        <= 3
    )

    # Indexes dropped during the generation are recreated
    assert get_item_index_names() == index_names


@override_settings(DEBUG=True)
def test_commands_create_perf_dataset_dev_user():
    """The development user should have a small drive with shares and a link trace."""
    call_command("create_perf_dataset", *SMALL_DATASET)

    user = models.User.objects.get(email="drive@drive.world")
    assert models.Item.objects.filter(creator=user).count() == 19
    assert models.ItemAccess.objects.filter(user=user).count() == 3
    assert models.LinkTrace.objects.filter(user=user).count() == 1
    assert models.ItemFavorite.objects.filter(user=user).count() == 1


@override_settings(DEBUG=True)
def test_commands_create_perf_dataset_requires_empty_database():
    """The command should refuse to run on a database that already has items."""
    factories.ItemFactory()

    with pytest.raises(CommandError, match="must not contain items"):
        call_command("create_perf_dataset", *SMALL_DATASET)


@override_settings(DEBUG=False)
def test_commands_create_perf_dataset_requires_debug():
    """The command should refuse to run outside of debug mode without --force."""
    with pytest.raises(CommandError, match="not meant to be used in production"):
        call_command("create_perf_dataset", *SMALL_DATASET)
