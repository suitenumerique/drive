"""Tests for the Item viewset search method with fulltext."""

import secrets
from json import loads as json_loads
from operator import itemgetter

from django.test import RequestFactory

import pytest
import responses
from rest_framework.test import APIClient

from core import factories, models
from core.services.search_indexers import get_file_indexer

pytestmark = pytest.mark.django_db


def build_search_url(**kwargs):
    """Build absolute uri for search endpoint with ORDERED query arguments"""
    return (
        RequestFactory()
        .get("/api/v1.0/items/search/", dict(sorted(kwargs.items())))
        .build_absolute_uri()
    )


@pytest.mark.usefixtures("indexer_settings")
@responses.activate
def test_api_items_search_authenticated_fulltext_query(indexer_settings):
    """
    Authenticated users should be able to search for items by title.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    indexer_settings.SEARCH_INDEXER_QUERY_URL = "http://find/api/v1.0/search"

    # Create items with predefined titles
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder_access = factories.UserItemAccessFactory(item=folder, user=user)
    _, item_b, item_c = factories.ItemFactory.create_batch(
        3, parent=folder, type=models.ItemTypeChoices.FILE
    )

    # Find response
    responses.add(
        responses.POST,
        "http://find/api/v1.0/search",
        json=[
            {"_id": str(item_b.pk)},
            {"_id": str(item_c.pk)},
        ],
        status=200,
    )

    response = client.get("/api/v1.0/items/search/?title=alpha")
    assert response.status_code == 200
    assert response.data["count"] == 2

    assert response.json()["results"] == [
        {
            "abilities": item_b.get_abilities(user),
            "ancestors_link_reach": item_b.ancestors_link_reach,
            "ancestors_link_role": item_b.ancestors_link_role,
            "computed_link_reach": item_b.computed_link_reach,
            "computed_link_role": item_b.computed_link_role,
            "created_at": item_b.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(item_b.creator.id),
                "full_name": item_b.creator.full_name,
                "short_name": item_b.creator.short_name,
            },
            "deleted_at": None,
            "depth": 2,
            "description": None,
            "filename": item_b.filename,
            "hard_delete_at": None,
            "id": str(item_b.id),
            "is_favorite": False,
            "is_wopi_supported": False,
            "link_reach": item_b.link_reach,
            "link_role": item_b.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 0,
            "numchild_folder": 0,
            "path": str(item_b.path),
            "size": None,
            "title": item_b.title,
            "type": "file",
            "updated_at": item_b.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": str(item_b.upload_state),
            "url": None,
            "url_preview": None,
            "user_role": folder_access.role,
            "parents": [
                {
                    "abilities": folder.get_abilities(user),
                    "ancestors_link_reach": folder.ancestors_link_reach,
                    "ancestors_link_role": folder.ancestors_link_role,
                    "computed_link_reach": folder.computed_link_reach,
                    "computed_link_role": folder.computed_link_role,
                    "created_at": folder.created_at.isoformat().replace("+00:00", "Z"),
                    "creator": {
                        "id": str(folder.creator.id),
                        "full_name": folder.creator.full_name,
                        "short_name": folder.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 1,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(folder.id),
                    "is_wopi_supported": False,
                    "link_reach": folder.link_reach,
                    "link_role": folder.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 3,
                    "numchild_folder": 0,
                    "path": str(folder.path),
                    "size": None,
                    "title": folder.title,
                    "type": "folder",
                    "updated_at": folder.updated_at.isoformat().replace("+00:00", "Z"),
                    "upload_state": None,
                    "url": None,
                    "url_preview": None,
                    "user_role": folder_access.role,
                },
            ],
        },
        {
            "abilities": item_c.get_abilities(user),
            "ancestors_link_reach": item_c.ancestors_link_reach,
            "ancestors_link_role": item_c.ancestors_link_role,
            "computed_link_reach": item_c.computed_link_reach,
            "computed_link_role": item_c.computed_link_role,
            "created_at": item_c.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(item_c.creator.id),
                "full_name": item_c.creator.full_name,
                "short_name": item_c.creator.short_name,
            },
            "deleted_at": None,
            "depth": 2,
            "description": None,
            "filename": item_c.filename,
            "hard_delete_at": None,
            "id": str(item_c.id),
            "is_favorite": False,
            "is_wopi_supported": False,
            "link_reach": item_c.link_reach,
            "link_role": item_c.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 0,
            "numchild_folder": 0,
            "path": str(item_c.path),
            "size": None,
            "title": item_c.title,
            "type": "file",
            "updated_at": item_c.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": str(item_c.upload_state),
            "url": None,
            "url_preview": None,
            "user_role": folder_access.role,
            "parents": [
                {
                    "abilities": folder.get_abilities(user),
                    "ancestors_link_reach": folder.ancestors_link_reach,
                    "ancestors_link_role": folder.ancestors_link_role,
                    "computed_link_reach": folder.computed_link_reach,
                    "computed_link_role": folder.computed_link_role,
                    "created_at": folder.created_at.isoformat().replace("+00:00", "Z"),
                    "creator": {
                        "id": str(folder.creator.id),
                        "full_name": folder.creator.full_name,
                        "short_name": folder.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 1,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(folder.id),
                    "is_wopi_supported": False,
                    "link_reach": folder.link_reach,
                    "link_role": folder.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 3,
                    "numchild_folder": 0,
                    "path": str(folder.path),
                    "size": None,
                    "title": folder.title,
                    "type": "folder",
                    "updated_at": folder.updated_at.isoformat().replace("+00:00", "Z"),
                    "upload_state": None,
                    "url": None,
                    "url_preview": None,
                    "user_role": folder_access.role,
                },
            ],
        },
    ]


@responses.activate
@pytest.mark.parametrize(
    "pagination, status, expected",
    (
        (
            {"page": 1},
            200,
            {
                "count": 30,
                "previous": None,
                "next": {"page": 2},
                "range": (0, 20),
            },
        ),
        (
            {},
            200,
            {
                "count": 30,
                "previous": None,
                "next": {"page": 2},
                "range": (0, 20),
                "api_page_size": 21,  # default page_size is 20
            },
        ),
        (
            {"page": 3},
            404,
            {},
        ),
        (
            {"page": 1},
            200,
            {
                "count": 30,
                "previous": None,
                "next": {"page": 2},
                "range": (0, 20),
            },
        ),
        (
            {"page": 2},
            200,
            {
                "count": 30,
                "previous": {},
                "next": None,
                "range": (20, 30),
            },
        ),
    ),
)
def test_api_items_search_pagination(indexer_settings, pagination, status, expected):
    """Files should be ordered by descending "score" by default"""
    indexer_settings.SEARCH_INDEXER_QUERY_URL = "http://find/api/v1.0/search"

    assert get_file_indexer() is not None

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    items = factories.ItemFactory.create_batch(
        30,
        title="alpha",
        users=[user],
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
        parent=parent,
    )

    items_by_uuid = {str(item.pk): item for item in items}

    # reverse sort by random score to simulate score ordering
    api_results = sorted(
        [
            {"_id": id, "score": (secrets.randbelow(1000) / 1000.0)}
            for id in items_by_uuid.keys()
        ],
        key=itemgetter("score"),
        reverse=True,
    )

    # Find response
    # pylint: disable-next=assignment-from-none
    api_search = responses.add(
        responses.POST,
        "http://find/api/v1.0/search",
        json=api_results,
        status=200,
    )

    response = client.get(
        "/api/v1.0/items/search/",
        data={
            "title": "alpha",
            **pagination,
        },
    )

    assert response.status_code == status

    if response.status_code < 300:
        previous_url = (
            build_search_url(title="alpha", **expected["previous"])
            if expected.get("previous") is not None
            else None
        )
        next_url = (
            build_search_url(title="alpha", **expected["next"])
            if expected.get("next") is not None
            else None
        )
        start, end = expected["range"]

        content = response.json()
        results = content.pop("results")

        # The find api results ordering by score is kept
        assert [r["id"] for r in results] == [r["_id"] for r in api_results[start:end]]
        assert content["count"] == expected["count"]
        assert content["previous"] == previous_url
        assert content["next"] == next_url

        # Check the query parameters.
        assert api_search.call_count == 1
        assert api_search.calls[0].response.status_code == 200
        assert json_loads(api_search.calls[0].request.body) == {
            "q": "alpha",
            "visited": [],
            "services": ["drive"],
            "nb_results": 50,
        }


@responses.activate
@pytest.mark.parametrize(
    "pagination, status, expected",
    (
        (
            {"page": 1},
            200,
            {
                "count": 30,
                "previous": None,
                "next": {"page": 2},
                "range": (0, 20),
            },
        ),
        (
            {},
            200,
            {
                "count": 30,
                "previous": None,
                "next": {"page": 2},
                "range": (0, 20),
                "api_page_size": 21,  # default page_size is 20
            },
        ),
        (
            {"page": 3},
            404,
            {},
        ),
        (
            {"page": 1},
            200,
            {
                "count": 30,
                "previous": None,
                "next": {"page": 2},
                "range": (0, 20),
            },
        ),
        (
            {"page": 2},
            200,
            {
                "count": 30,
                "previous": {},
                "next": None,
                "range": (20, 30),
            },
        ),
    ),
)
def test_api_items_search_pagination_endpoint_is_none(
    indexer_settings, pagination, status, expected
):
    """Files are filtered and ordered (created_at)"""
    indexer_settings.SEARCH_INDEXER_QUERY_URL = None

    assert get_file_indexer() is None

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    factories.ItemFactory.create_batch(
        30,
        title="alpha",
        users=[user],
        parent=parent,
    )

    response = client.get(
        "/api/v1.0/items/search/",
        data={
            "title": "alpha",
            **pagination,
        },
    )

    assert response.status_code == status

    if response.status_code < 300:
        previous_url = (
            build_search_url(title="alpha", **expected["previous"])
            if expected.get("previous") is not None
            else None
        )
        next_url = (
            build_search_url(title="alpha", **expected["next"])
            if expected.get("next") is not None
            else None
        )
        queryset = parent.descendants().order_by("created_at")
        start, end = expected["range"]
        expected_results = [str(d.pk) for d in queryset[start:end]]

        content = response.json()
        results = content.pop("results")

        assert [r["id"] for r in results] == expected_results
        assert content["count"] == expected["count"]
        assert content["previous"] == previous_url
        assert content["next"] == next_url


def test_api_items_search_feature_disabled(indexer_settings):
    """Should not use indexed search if the feature is disabled"""
    indexer_settings.FEATURES_INDEXED_SEARCH = False

    assert get_file_indexer() is not None

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    docs = factories.ItemFactory.create_batch(
        5,
        title="alpha",
        users=[user],
        parent=parent,
    )

    response = client.get(
        "/api/v1.0/items/search/",
        data={
            "title": "alpha",
        },
    )

    assert response.status_code == 200

    content = response.json()
    results = content.pop("results")

    assert [r["id"] for r in results] == [str(d.pk) for d in docs]
