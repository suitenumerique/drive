"""Batch deletion preflight: permissions, metadata and bounded query cost."""

import uuid

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db
URL = "/api/v1.0/items/deletion-info/"


def setup_selection():
    """An owned tree with a deeply nested restriction and an ordinary file."""
    owner = factories.UserFactory()
    parent = factories.ItemFactory(type="folder", users=[(owner, "owner")])
    child = factories.ItemFactory(type="folder", parent=parent)
    target = factories.ItemFactory(type="folder", parent=child).restrict(owner)
    entry = models.Item.objects.get(target=target)
    file = factories.ItemFactory(parent=parent)
    client = APIClient()
    client.force_login(owner)
    return client, parent, child, target, entry, file


def test_deletion_info_complete_map():
    """Only physical ancestors of active restriction entries require confirmation."""
    client, parent, child, target, entry, file = setup_selection()
    items = [parent, child, target, entry, file, parent]
    response = client.post(URL, {"ids": [str(item.pk) for item in items]}, format="json")
    assert response.status_code == 200
    assert response.json() == {
        str(item.pk): {"hasRestrictedDescendent": item in (parent, child)} for item in items
    }
    assert models.Item.objects.get(pk=parent.pk).deleted_at is None


@pytest.mark.parametrize("payload", [{}, {"ids": []}, {"ids": ["invalid"]}, {"ids": "bad"}])
def test_deletion_info_invalid(payload):
    """Reject malformed and empty requests."""
    client = APIClient()
    client.force_login(factories.UserFactory())
    assert client.post(URL, payload, format="json").status_code == 400


@pytest.mark.parametrize("missing", [True, False])
def test_deletion_info_all_or_nothing(missing):
    """A single inaccessible or missing item fails the complete request."""
    client, parent, *_ = setup_selection()
    other_id = uuid.uuid4() if missing else factories.ItemFactory().pk
    response = client.post(URL, {"ids": [str(parent.pk), str(other_id)]}, format="json")
    assert response.status_code == (404 if missing else 403)
    assert str(parent.pk) not in response.json()


@pytest.mark.parametrize("stale", ["entry", "target", "missing_target"])
def test_deletion_info_stale_restrictions(stale):
    """Deleted entries and targets do not require confirmation."""
    client, parent, _, target, entry, _ = setup_selection()
    if stale == "missing_target":
        models.Item.objects.filter(pk=target.pk).delete()
    else:
        models.Item.objects.filter(pk=entry.pk if stale == "entry" else target.pk).update(
            deleted_at=timezone.now()
        )
    response = client.post(URL, {"ids": [str(parent.pk)]}, format="json")
    assert response.status_code == 200
    assert response.json() == {str(parent.pk): {"hasRestrictedDescendent": False}}


def test_deletion_info_query_count():
    """Selection size adds neither permission nor descendant queries."""
    client, parent, child, target, entry, file = setup_selection()
    counts = []
    for items in [[child], [parent, child, target, entry, file]]:
        with CaptureQueriesContext(connection) as queries:
            response = client.post(URL, {"ids": [str(item.pk) for item in items]}, format="json")
        assert response.status_code == 200
        counts.append(len(queries))
    assert counts[0] == counts[1]


def test_deletion_info_does_not_follow_detached_targets():
    """Nested restrictions inside detached targets do not affect an unrelated physical tree."""
    client, parent, _, target, entry, _ = setup_selection()
    owner = models.ItemAccess.objects.get(item=parent, role="owner").user
    factories.ItemFactory(type="folder", parent=target).restrict(owner)
    models.Item.objects.filter(pk=entry.pk).delete()
    response = client.post(URL, {"ids": [str(parent.pk), str(target.pk)]}, format="json")
    assert response.status_code == 200
    assert response.json() == {
        str(parent.pk): {"hasRestrictedDescendent": False},
        str(target.pk): {"hasRestrictedDescendent": True},
    }


@pytest.mark.parametrize("authenticated", [False, True])
def test_deletion_info_link_access_does_not_allow_deletion(authenticated):
    """Read access through links is not sufficient for deletion metadata."""
    item = factories.ItemFactory(type="folder", link_reach=models.LinkReachChoices.PUBLIC)
    client = APIClient()
    if authenticated:
        client.force_login(factories.UserFactory())
    response = client.post(URL, {"ids": [str(item.pk)]}, format="json")
    assert response.status_code in (401, 403)


def test_deletion_info_queries_across_trees():
    """Ancestor links are loaded in a single batch even for independent trees."""
    owner = factories.UserFactory()
    items = []
    for _ in range(5):
        root = factories.ItemFactory(type="folder", users=[(owner, "owner")])
        items.append(factories.ItemFactory(type="folder", parent=root))
    client = APIClient()
    client.force_login(owner)
    counts = []
    for selection in [items[:1], items]:
        with CaptureQueriesContext(connection) as queries:
            response = client.post(
                URL, {"ids": [str(item.pk) for item in selection]}, format="json"
            )
        assert response.status_code == 200
        counts.append(len(queries))
    assert counts[0] == counts[1]
