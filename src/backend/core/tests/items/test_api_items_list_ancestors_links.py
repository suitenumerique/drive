"""Tests for the inherited links of the items listed from several trees."""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers

pytestmark = pytest.mark.django_db


def _serialized(item, user):
    """Build the expected representation of a folder, computed item by item."""
    # A fresh instance without the listing annotations goes through the per-item
    # computations of the model, independent from the grouped ancestors lookup
    item = models.Item.objects.annotate_with_numchild().get(pk=item.pk)
    return {
        "id": str(item.id),
        "abilities": item.get_abilities(user),
        "ancestors_link_reach": item.ancestors_link_reach,
        "ancestors_link_role": item.ancestors_link_role,
        "computed_link_reach": item.computed_link_reach,
        "computed_link_role": item.computed_link_role,
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "id": str(item.creator.id),
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": item.depth,
        "is_favorite": False,
        "is_restricted": item.is_restricted,
        "target": None,
        "link_reach": item.link_reach,
        "link_role": item.link_role,
        "nb_accesses": item.nb_accesses,
        "numchild": item.numchild,
        "numchild_folder": item.numchild_folder,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_role": item.get_role(user),
        "type": models.ItemTypeChoices.FOLDER,
        "upload_state": None,
        "url": None,
        "url_permalink": None,
        "url_preview": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": None,
        "size": None,
        "description": None,
        "deleted_at": None,
        "hard_delete_at": None,
        "is_wopi_supported": False,
    }


def _folder(**kwargs):
    """Create a folder."""
    return factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, **kwargs)


def _build_trees(user):
    """Create trees visited by the user through links, return the listed and hidden folders."""
    # Tree A: the visited folder inherits an open link from its root
    root_a = _folder(link_reach="public", link_role="editor")
    child_a = _folder(parent=root_a, link_traces=[user])

    # Tree B: the link is inherited through two levels
    root_b = _folder(link_reach="authenticated", link_role="reader")
    mid_b = _folder(parent=root_b, link_reach=None)
    child_b = _folder(parent=mid_b, link_traces=[user])

    # Tree C: the root link was closed after the visit
    root_c = _folder(link_reach="public")
    child_c = _folder(parent=root_c, link_traces=[user])
    root_c.link_reach = "restricted"
    root_c.save()

    # Tree D: an ancestor of the visited folder was deleted
    root_d = _folder(link_reach="public")
    mid_d = _folder(parent=root_d)
    child_d = _folder(parent=mid_d, link_traces=[user])
    mid_d.soft_delete()

    # Tree E: the visited folder sits under a restricted folder carrying the link
    owner = factories.UserFactory()
    container = _folder()
    folder_e = _folder(parent=container, users=[(owner, "owner")])
    folder_e = folder_e.restrict(owner)
    folder_e.link_reach = "public"
    folder_e.link_role = "reader"
    folder_e.save()
    child_e = _folder(parent=folder_e, link_traces=[user])

    # A folder the user owns directly
    own = _folder(users=[(user, "owner")])

    return [child_a, child_b, child_e, own], [root_c, child_c, root_d, child_d, folder_e]


def test_api_items_list_ancestors_links_across_trees():
    """Listed roots carry the links inherited in their own tree, with full responses."""
    user = factories.UserFactory()
    listed, hidden = _build_trees(user)

    client = APIClient()
    client.force_login(user)
    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = {result["id"]: result for result in response.json()["results"]}
    assert set(results) == {str(item.id) for item in listed}
    assert not set(results) & {str(item.id) for item in hidden}
    for item in listed:
        assert results[str(item.id)] == _serialized(item, user)


def test_api_items_favorites_ancestors_links_across_trees():
    """Favorites carry the links inherited in their own tree, with full responses."""
    user = factories.UserFactory()
    listed, hidden = _build_trees(user)
    for item in listed + hidden:
        models.ItemFavorite.objects.create(item=item, user=user)

    client = APIClient()
    client.force_login(user)
    response = client.get("/api/v1.0/items/favorites/")

    assert response.status_code == 200
    results = {result["id"]: result for result in response.json()["results"]}
    assert set(results) == {str(item.id) for item in listed}
    # The favorites use a lighter serializer, whose abilities still depend on the links
    fields = serializers.ListItemLightSerializer.Meta.fields
    for item in listed:
        expected = {**_serialized(item, user), "is_favorite": True}
        assert results[str(item.id)] == {field: expected[field] for field in fields}


def _build_access_trees(user):
    """Create trees the user holds direct accesses in; search returns the accessed folders."""
    # Tree A: the accessed folder inherits an open link from its root
    root_a = _folder(link_reach="public", link_role="editor")
    child_a = _folder(parent=root_a, users=[(user, "reader")])

    # Tree B: the link is inherited through two levels, the middle one carrying no link
    root_b = _folder(link_reach="authenticated", link_role="reader")
    mid_b = _folder(parent=root_b, link_reach=None)
    child_b = _folder(parent=mid_b, users=[(user, "reader")])

    # Tree C: the accessed folder sits under a restricted folder
    owner = factories.UserFactory()
    container = _folder()
    folder_c = _folder(parent=container, users=[(owner, "owner")])
    folder_c = folder_c.restrict(owner)
    child_c = _folder(parent=folder_c, users=[(user, "reader")])

    # A folder the user owns directly
    own = _folder(users=[(user, "owner")])

    return [child_a, child_b, child_c, own], [root_a, root_b, mid_b, container, folder_c]


def _expected_search_payload(item, user):
    """Build the expected search representation, computed item by item."""
    ancestors = {
        str(ancestor.pk): ancestor
        for ancestor in models.Item.objects.filter(pk__in=list(item.path)[:-1])
    }
    # Parents absent from the results are serialized without the favorite
    # annotation, and the read-only field is skipped entirely: no is_favorite key.
    return {
        **_serialized(item, user),
        "parents": [
            {
                key: value
                for key, value in _serialized(ancestors[str(label)], user).items()
                if key != "is_favorite"
            }
            for label in list(item.path)[:-1]
        ],
    }


def test_api_items_search_ancestors_links_across_trees():
    """Search results and their parents carry the links of their own tree, fully serialized."""
    user = factories.UserFactory()
    searched, hidden = _build_access_trees(user)

    client = APIClient()
    client.force_login(user)
    response = client.get("/api/v1.0/items/search/")

    assert response.status_code == 200
    results = {result["id"]: result for result in response.json()["results"]}
    assert set(results) == {str(item.id) for item in searched}
    assert not set(results) & {str(item.id) for item in hidden}
    for item in searched:
        assert results[str(item.id)] == _expected_search_payload(item, user)


def test_api_items_search_ancestors_links_num_queries(django_assert_num_queries):
    """Search serializes results and parents without querying per item."""
    user = factories.UserFactory()
    searched, _hidden = _build_access_trees(user)

    client = APIClient()
    client.force_login(user)
    # Cold cache: one count per searched item and parent for its number of accesses.
    with django_assert_num_queries(14):
        response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 200
    assert {result["id"] for result in response.json()["results"]} == {
        str(item.id) for item in searched
    }

    # The numbers of accesses are now cached: the serialization itself is measured.
    with django_assert_num_queries(6):
        response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 200
