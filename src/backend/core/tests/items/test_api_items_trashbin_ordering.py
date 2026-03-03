"""Test the ordering of trashbin items."""

from datetime import datetime
from datetime import timezone as dt_tz

from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_trashbin_ordering_title():
    """Validate the ordering of trashbin items by title."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now()
    item_a = factories.ItemFactory(
        title="Abcd",
        type=models.ItemTypeChoices.FOLDER,
        deleted_at=now,
        users=[(user, "owner")],
    )
    item_z = factories.ItemFactory(
        title="Zyxc",
        type=models.ItemTypeChoices.FILE,
        deleted_at=now,
        users=[(user, "owner")],
    )

    # Ascending
    response = client.get("/api/v1.0/items/trashbin/?ordering=title")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_a.id)
    assert results[1]["id"] == str(item_z.id)

    # Descending
    response = client.get("/api/v1.0/items/trashbin/?ordering=-title")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_z.id)
    assert results[1]["id"] == str(item_a.id)


def test_api_items_trashbin_ordering_type():
    """Validate the ordering of trashbin items by type."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now()
    item_folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        deleted_at=now,
        users=[(user, "owner")],
    )
    item_file = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        deleted_at=now,
        users=[(user, "owner")],
    )

    # Ascending (FILE before FOLDER)
    response = client.get("/api/v1.0/items/trashbin/?ordering=type")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_file.id)
    assert results[1]["id"] == str(item_folder.id)

    # Descending (FOLDER before FILE)
    response = client.get("/api/v1.0/items/trashbin/?ordering=-type")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_folder.id)
    assert results[1]["id"] == str(item_file.id)


def test_api_items_trashbin_ordering_updated_at():
    """Validate the ordering of trashbin items by updated_at."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now()
    item_old = factories.ItemFactory(
        title="old_item",
        type=models.ItemTypeChoices.FOLDER,
        deleted_at=now,
        users=[(user, "owner")],
    )
    item_new = factories.ItemFactory(
        title="new_item",
        type=models.ItemTypeChoices.FOLDER,
        deleted_at=now,
        users=[(user, "owner")],
    )

    # Force different updated_at values
    models.Item.objects.filter(pk=item_old.pk).update(
        updated_at=datetime(2020, 1, 1, tzinfo=dt_tz.utc)
    )
    models.Item.objects.filter(pk=item_new.pk).update(
        updated_at=datetime(2025, 1, 1, tzinfo=dt_tz.utc)
    )

    # Ascending (oldest first)
    response = client.get("/api/v1.0/items/trashbin/?ordering=updated_at")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_old.id)
    assert results[1]["id"] == str(item_new.id)

    # Descending (newest first)
    response = client.get("/api/v1.0/items/trashbin/?ordering=-updated_at")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_new.id)
    assert results[1]["id"] == str(item_old.id)
