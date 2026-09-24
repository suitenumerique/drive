"""
Unit tests for the lookups relying on item paths being made of item ids
"""

from unittest import mock

from django.db.models import F, Value

import pytest
from rest_framework.test import APIRequestFactory

from core import factories, models
from core.api.serializers import ListItemSerializer

pytestmark = pytest.mark.django_db


@pytest.fixture(name="tree")
def fixture_tree():
    """
    Build two trees:
        root > parent > child
             > sibling > nephew
        other_root
    """
    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    sibling = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    nephew = factories.ItemFactory(parent=sibling, type=models.ItemTypeChoices.FOLDER)
    other_root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    return {
        "root": root,
        "parent": parent,
        "child": child,
        "sibling": sibling,
        "nephew": nephew,
        "other_root": other_root,
    }


def test_models_items_id_in_path(tree):
    """IdInPath should match the item at a path and its ancestors only."""
    accesses = {name: factories.UserItemAccessFactory(item=item) for name, item in tree.items()}

    matched = models.ItemAccess.objects.filter(
        models.IdInPath(F("item_id"), Value(str(tree["child"].path)))
    )

    assert set(matched) == {accesses["root"], accesses["parent"], accesses["child"]}


def test_models_items_id_in_subtrees(tree):
    """IdInSubtrees should match the same items as OR-ing descendants lookups."""
    paths = [tree["parent"].path, tree["other_root"].path]

    matched = models.Item.objects.filter(models.IdInSubtrees(F("id"), paths))

    assert set(matched) == {tree["parent"], tree["child"], tree["other_root"]}
    assert set(matched) == set(
        models.Item.objects.filter(path__descendants=paths[0])
        | models.Item.objects.filter(path__descendants=paths[1])
    )


def test_models_items_path_in_subtree_lookup(tree):
    """The in_subtree lookup should match the same items as the descendants lookup."""
    matched = models.Item.objects.filter(path__in_subtree=tree["parent"].path)

    assert set(matched) == {tree["parent"], tree["child"]}
    assert set(matched) == set(models.Item.objects.filter(path__descendants=tree["parent"].path))

    matched = models.Item.objects.filter(path__in_subtree=tree["root"].path)

    assert set(matched) == {
        tree["root"],
        tree["parent"],
        tree["child"],
        tree["sibling"],
        tree["nephew"],
    }


def test_models_items_numchild_annotation_ignores_siblings_subtrees(tree):
    """The children of a sibling or of a child should not be counted."""
    item = models.Item.objects.annotate_with_numchild().get(pk=tree["parent"].pk)
    assert item.numchild == 1
    assert item.numchild_folder == 1

    item = models.Item.objects.annotate_with_numchild().get(pk=tree["root"].pk)
    assert item.numchild == 2
    assert item.numchild_folder == 2


def test_models_items_compute_items_ancestors_links_paths_mapping(tree, django_assert_num_queries):
    """
    The mapping computed at once for several items should match, at the parent path of
    each item, the mapping computed on each item.
    """
    tree["root"].link_reach = models.LinkReachChoices.AUTHENTICATED
    tree["root"].save()
    tree["sibling"].link_reach = models.LinkReachChoices.PUBLIC
    tree["sibling"].save()
    items = [tree["child"], tree["nephew"], tree["parent"], tree["other_root"]]

    with django_assert_num_queries(1):
        mapping = models.Item.compute_items_ancestors_links_paths_mapping(items)

    for item in items:
        parent_path = str(item.path[:-1])
        expected = item.compute_ancestors_links_paths_mapping().get(parent_path, [])
        assert mapping.get(parent_path, []) == expected


def test_models_items_compute_items_ancestors_links_paths_mapping_roots(
    tree, django_assert_num_queries
):
    """No query should be needed when all the items are roots."""
    with django_assert_num_queries(0):
        mapping = models.Item.compute_items_ancestors_links_paths_mapping(
            [tree["root"], tree["other_root"]]
        )

    assert not mapping


def test_models_items_serializer_fetches_wopi_configuration_once():
    """The WOPI configuration should be fetched once for all the serialized items."""
    user = factories.UserFactory()
    items = factories.ItemFactory.create_batch(
        3,
        type=models.ItemTypeChoices.FILE,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    request = APIRequestFactory().get("/")
    request.user = user

    with mock.patch(
        "wopi.utils.get_wopi_configuration", return_value={"extensions": {}, "mimetypes": {}}
    ) as get_wopi_configuration:
        data = ListItemSerializer(
            models.Item.objects.annotate_user_roles(user).filter(pk__in=[i.pk for i in items]),
            many=True,
            context={"request": request},
        ).data

    assert len(data) == 3
    get_wopi_configuration.assert_called_once()
