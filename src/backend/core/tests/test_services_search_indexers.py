"""Tests for Documents search indexers"""

from functools import partial
from json import dumps as json_dumps
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

import pytest
import responses
from factory import fuzzy
from requests import HTTPError

from core import factories, models
from core.services.search_indexers import (
    BaseItemIndexer,
    SearchIndexer,
    get_ancestor_to_descendants_map,
    get_file_indexer,
    get_visited_items_ids_of,
)

pytestmark = pytest.mark.django_db


class FakeDocumentIndexer(BaseItemIndexer):
    """Fake indexer for test purpose"""

    def serialize_item(self, item, accesses):
        return {}

    def push(self, data):
        pass

    def search_query(self, data, token):
        return {}


def test_get_ancestor_to_descendants_map():
    """Test ancestor mapping of a multiple paths."""
    root = factories.ItemFactory(title="root", type=models.ItemTypeChoices.FOLDER)
    a = factories.ItemFactory(
        title="a", type=models.ItemTypeChoices.FOLDER, parent=root
    )
    a_1 = factories.ItemFactory(title="a.1", type=models.ItemTypeChoices.FILE, parent=a)
    a_a = factories.ItemFactory(
        title="a.a", type=models.ItemTypeChoices.FOLDER, parent=a
    )
    a_a_1 = factories.ItemFactory(
        title="a.a.1", type=models.ItemTypeChoices.FILE, parent=a_a
    )
    b = factories.ItemFactory(
        title="b", type=models.ItemTypeChoices.FOLDER, parent=root
    )
    b_1 = factories.ItemFactory(title="b.1", type=models.ItemTypeChoices.FILE, parent=b)

    result = get_ancestor_to_descendants_map(
        [
            a_1,
            a_a_1,
            b_1,
        ]
    )

    assert dict(result) == {
        str(root.path): {
            str(a_1.path),
            str(a_a_1.path),
            str(b_1.path),
        },
        str(a.path): {
            str(a_1.path),
            str(a_a_1.path),
        },
        str(a_a.path): {
            str(a_a_1.path),
        },
        str(a_1.path): {
            str(a_1.path),
        },
        str(a_a_1.path): {
            str(a_a_1.path),
        },
        str(b.path): {
            str(b_1.path),
        },
        str(b_1.path): {
            str(b_1.path),
        },
    }


def test_services_search_indexer_class_invalid(indexer_settings):
    """
    Should raise RuntimeError if SEARCH_INDEXER_CLASS cannot be imported.
    """
    indexer_settings.SEARCH_INDEXER_CLASS = "unknown.Unknown"

    assert get_file_indexer() is None


def test_services_search_indexer_class(indexer_settings):
    """
    Import indexer class defined in setting SEARCH_INDEXER_CLASS.
    """
    indexer_settings.SEARCH_INDEXER_CLASS = (
        "core.tests.test_services_search_indexers.FakeDocumentIndexer"
    )

    assert isinstance(
        get_file_indexer(),
        import_string("core.tests.test_services_search_indexers.FakeDocumentIndexer"),
    )


def test_services_search_indexer_is_configured(indexer_settings):
    """
    Should return true only when the indexer class and other configuration settings
    are valid.
    """
    indexer_settings.SEARCH_INDEXER_CLASS = None

    # None
    get_file_indexer.cache_clear()
    assert not get_file_indexer()

    # Empty
    indexer_settings.SEARCH_INDEXER_CLASS = ""

    get_file_indexer.cache_clear()
    assert not get_file_indexer()

    # Valid class
    indexer_settings.SEARCH_INDEXER_CLASS = (
        "core.services.search_indexers.SearchIndexer"
    )

    get_file_indexer.cache_clear()
    assert get_file_indexer() is not None

    indexer_settings.SEARCH_INDEXER_URL = ""

    # Invalid url
    get_file_indexer.cache_clear()
    assert not get_file_indexer()


def test_services_search_indexer_url_is_none(indexer_settings):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_URL is None or empty.
    """
    indexer_settings.SEARCH_INDEXER_URL = None

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert "SEARCH_INDEXER_URL must be set in Django settings." in str(exc_info.value)


def test_services_search_indexer_url_is_empty(indexer_settings):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_URL is empty string.
    """
    indexer_settings.SEARCH_INDEXER_URL = ""

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert "SEARCH_INDEXER_URL must be set in Django settings." in str(exc_info.value)


def test_services_search_indexer_secret_is_none(indexer_settings):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_SECRET is None.
    """
    indexer_settings.SEARCH_INDEXER_SECRET = None

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert "SEARCH_INDEXER_SECRET must be set in Django settings." in str(
        exc_info.value
    )


def test_services_search_indexer_secret_is_empty(indexer_settings):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_SECRET is empty string.
    """
    indexer_settings.SEARCH_INDEXER_SECRET = ""

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert "SEARCH_INDEXER_SECRET must be set in Django settings." in str(
        exc_info.value
    )


def test_services_search_endpoint_is_none(indexer_settings):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_QUERY_URL is None.
    """
    indexer_settings.SEARCH_INDEXER_QUERY_URL = None

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert "SEARCH_INDEXER_QUERY_URL must be set in Django settings." in str(
        exc_info.value
    )


def test_services_search_endpoint_is_empty(indexer_settings):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_QUERY_URL is empty.
    """
    indexer_settings.SEARCH_INDEXER_QUERY_URL = ""

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert "SEARCH_INDEXER_QUERY_URL must be set in Django settings." in str(
        exc_info.value
    )


@pytest.mark.parametrize(
    "mimetypes, expected",
    [
        ("", "SEARCH_INDEXER_ALLOWED_MIMETYPES must be set in Django settings."),
        (None, "SEARCH_INDEXER_ALLOWED_MIMETYPES must be set in Django settings."),
        ((), "SEARCH_INDEXER_ALLOWED_MIMETYPES must be set in Django settings."),
        (12, "SEARCH_INDEXER_ALLOWED_MIMETYPES Django setting must be a list."),
    ],
)
def test_services_search_allowed_mimetypes_is_invalid(
    indexer_settings, mimetypes, expected
):
    """
    Indexer should raise RuntimeError if SEARCH_INDEXER_ALLOWED_MIMETYPES is either empty, None
    or not a list
    """
    indexer_settings.SEARCH_INDEXER_ALLOWED_MIMETYPES = mimetypes

    with pytest.raises(ImproperlyConfigured) as exc_info:
        SearchIndexer()

    assert expected in str(exc_info.value)


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_item_file():
    """
    It should serialize files with correct metadata and access control.
    """
    user_a, user_b = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(
        upload_bytes=b"This is a text file content",
        mimetype="application/pdf",
        type=models.ItemTypeChoices.FILE,
    )

    factories.UserItemAccessFactory(item=item, user=user_a)
    factories.UserItemAccessFactory(item=item, user=user_b)
    factories.TeamItemAccessFactory(item=item, team="team1")
    factories.TeamItemAccessFactory(item=item, team="team2")

    accesses = {
        str(item.path): {
            "users": {str(user_a.sub), str(user_b.sub)},
            "teams": {"team1", "team2"},
        }
    }

    indexer = SearchIndexer()
    result = indexer.serialize_item(item, accesses)

    assert set(result.pop("users")) == {str(user_a.sub), str(user_b.sub)}
    assert set(result.pop("groups")) == {"team1", "team2"}
    assert result == {
        "id": str(item.id),
        "title": item.title,
        "description": "",
        "depth": 1,
        "path": str(item.path),
        "numchild": 0,
        "mimetype": "application/pdf",
        "content": "",
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "reach": item.link_reach,
        "size": item.size,
        "is_active": True,
    }


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_item_folder():
    """
    It should serialize folder with correct metadata and access control.
    """
    user_a, user_b = factories.UserFactory.create_batch(2)
    folder = factories.ItemFactory(
        description="Any description",
        mimetype="text/plain",
        type=models.ItemTypeChoices.FOLDER,
    )

    factories.UserItemAccessFactory(item=folder, user=user_a)
    factories.UserItemAccessFactory(item=folder, user=user_b)
    factories.TeamItemAccessFactory(item=folder, team="team1")
    factories.TeamItemAccessFactory(item=folder, team="team2")

    accesses = {
        str(folder.path): {
            "users": {str(user_a.sub), str(user_b.sub)},
            "teams": {"team1", "team2"},
        }
    }

    indexer = SearchIndexer()
    result = indexer.serialize_item(folder, accesses)

    assert set(result.pop("users")) == {str(user_a.sub), str(user_b.sub)}
    assert set(result.pop("groups")) == {"team1", "team2"}
    assert result == {
        "id": str(folder.id),
        "title": folder.title,
        "description": "Any description",
        "depth": 1,
        "path": str(folder.path),
        "numchild": 0,
        "mimetype": "text/plain",
        "content": "",
        "created_at": folder.created_at.isoformat(),
        "updated_at": folder.updated_at.isoformat(),
        "reach": folder.link_reach,
        "size": 0,
        "is_active": True,
    }


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_item_textfile():
    """
    It should serialize text files with correct metadata and access control.
    """
    user_a, user_b = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(
        upload_bytes=b"This is a text file content",
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    factories.UserItemAccessFactory(item=item, user=user_a)
    factories.UserItemAccessFactory(item=item, user=user_b)
    factories.TeamItemAccessFactory(item=item, team="team1")
    factories.TeamItemAccessFactory(item=item, team="team2")

    accesses = {
        str(item.path): {
            "users": {str(user_a.sub), str(user_b.sub)},
            "teams": {"team1", "team2"},
        }
    }

    indexer = SearchIndexer()
    result = indexer.serialize_item(item, accesses)

    assert set(result.pop("users")) == {str(user_a.sub), str(user_b.sub)}
    assert set(result.pop("groups")) == {"team1", "team2"}
    assert result == {
        "id": str(item.id),
        "title": item.title,
        "description": "",
        "depth": 1,
        "path": str(item.path),
        "numchild": 0,
        "mimetype": "text/plain",
        "content": "This is a text file content",
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "reach": item.link_reach,
        "size": len("This is a text file content"),
        "is_active": True,
    }


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_document_deleted():
    """Deleted documents are marked as just in the serialized json."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
    )

    folder.soft_delete()
    item.refresh_from_db()

    indexer = SearchIndexer()
    result = indexer.serialize_item(item, {})

    assert result["is_active"] is False


@responses.activate
def test_services_search_indexers_index_errors(indexer_settings):
    """
    Documents indexing response handling on Find API HTTP errors.
    """
    factories.ItemFactory(
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes=b"This is a text file",
    )

    indexer_settings.SEARCH_INDEXER_URL = "http://app-find/api/v1.0/documents/index/"

    responses.add(
        responses.POST,
        "http://app-find/api/v1.0/documents/index/",
        status=401,
        body=json_dumps({"message": "Authentication failed."}),
    )

    with pytest.raises(HTTPError):
        SearchIndexer().index()


@patch.object(SearchIndexer, "push")
def test_services_search_indexers_batches_pass_only_batch_accesses(
    mock_push, indexer_settings
):
    """
    Items indexing should be processed in batches,
    and only the access data relevant to each batch should be used.
    """
    indexer_settings.SEARCH_INDEXER_BATCH_SIZE = 2
    items = factories.ItemFactory.create_batch(
        5,
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes="this is a text",
    )

    # Attach a single user access to each file
    expected_user_subs = {}
    for item in items:
        access = factories.UserItemAccessFactory(item=item)
        expected_user_subs[str(item.id)] = str(access.user.sub)

    assert SearchIndexer().index() == 5

    # Should be 3 batches: 2 + 2 + 1
    assert mock_push.call_count == 3

    seen_item_ids = set()

    for call in mock_push.call_args_list:
        batch = call.args[0]
        assert isinstance(batch, list)

        for item_json in batch:
            item_id = item_json["id"]
            seen_item_ids.add(item_id)

            # Only one user expected per document
            assert item_json["users"] == [expected_user_subs[item_id]]
            assert item_json["groups"] == []

    # Make sure all 5 files were indexed
    assert seen_item_ids == {str(d.id) for d in items}


@patch.object(SearchIndexer, "push")
@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_ignore_content_if_not_ready(mock_push):
    """
    File indexing should be processed in batches,
    and only the access data relevant to each batch should be used.
    """
    item = factories.ItemFactory(
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes="this is a text",
    )

    # wrong mimetype
    pdf_item = factories.ItemFactory(
        mimetype="application/pdf",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes="this is a PDF",
    )

    # not ready
    not_ready_items = factories.ItemFactory.create_batch(
        5,
        mimetype="text/plain",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=fuzzy.FuzzyChoice(
            [
                models.ItemUploadStateChoices.PENDING,
                models.ItemUploadStateChoices.ANALYZING,
                models.ItemUploadStateChoices.SUSPICIOUS,
                models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE,
            ]
        ),
        upload_bytes="this is a text",
    )

    assert SearchIndexer().index() == 7

    assert mock_push.call_count == 1

    results = {item["id"]: item["content"] for item in mock_push.call_args[0][0]}
    assert results == {
        str(item.id): "this is a text",
        str(pdf_item.id): "",
        **{str(item.id): "" for item in not_ready_items},
    }


@patch.object(SearchIndexer, "push")
@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_ancestors_link_reach(mock_push):
    """Document accesses and reach should take into account ancestors link reaches."""
    great_grand_parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach="restricted",
    )
    grand_parent = factories.ItemFactory(
        parent=great_grand_parent,
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach="authenticated",
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach="public",
    )
    document = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes=b"This is a text file",
        link_reach="restricted",
    )

    assert SearchIndexer().index() == 4

    results = {doc["id"]: doc for doc in mock_push.call_args[0][0]}
    assert len(results) == 4
    assert results[str(great_grand_parent.id)]["reach"] == "restricted"
    assert results[str(grand_parent.id)]["reach"] == "authenticated"
    assert results[str(parent.id)]["reach"] == "public"
    assert results[str(document.id)]["reach"] == "restricted"


@patch.object(SearchIndexer, "push")
@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_ancestors_users(mock_push):
    """Document accesses and reach should include users from ancestors."""
    user_gp, user_p, user_d = factories.UserFactory.create_batch(3)

    grand_parent = factories.ItemFactory(
        users=[user_gp],
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        users=[user_p],
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    document = factories.ItemFactory(
        parent=parent,
        users=[user_d],
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes=b"This is a text file",
    )

    assert SearchIndexer().index() == 3

    results = {doc["id"]: doc for doc in mock_push.call_args[0][0]}
    assert len(results) == 3
    assert results[str(grand_parent.id)]["users"] == [str(user_gp.sub)]
    assert set(results[str(parent.id)]["users"]) == {str(user_gp.sub), str(user_p.sub)}
    assert set(results[str(document.id)]["users"]) == {
        str(user_gp.sub),
        str(user_p.sub),
        str(user_d.sub),
    }


@patch.object(SearchIndexer, "push")
@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_ancestors_teams(mock_push):
    """Document accesses and reach should include teams from ancestors."""
    grand_parent = factories.ItemFactory(
        teams=["team_gp"],
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        teams=["team_p"],
        type=models.ItemTypeChoices.FOLDER,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    document = factories.ItemFactory(
        parent=parent,
        teams=["team_d"],
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        upload_bytes=b"This is a text file",
    )

    assert SearchIndexer().index() == 3

    results = {doc["id"]: doc for doc in mock_push.call_args[0][0]}
    assert len(results) == 3
    assert results[str(grand_parent.id)]["groups"] == ["team_gp"]
    assert set(results[str(parent.id)]["groups"]) == {"team_gp", "team_p"}
    assert set(results[str(document.id)]["groups"]) == {"team_gp", "team_p", "team_d"}


@patch("requests.post")
def test_push_uses_correct_url_and_data(mock_post, indexer_settings):
    """
    push() should call requests.post with the correct URL from settings
    the timeout set to 10 seconds and the data as JSON.
    """
    indexer_settings.SEARCH_INDEXER_URL = "http://example.com/index"

    indexer = SearchIndexer()
    sample_data = [{"id": "123", "title": "Test"}]

    mock_response = mock_post.return_value
    mock_response.raise_for_status.return_value = None  # No error

    indexer.push(sample_data)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    assert args[0] == indexer_settings.SEARCH_INDEXER_URL
    assert kwargs.get("json") == sample_data
    assert kwargs.get("timeout") == 10


def test_get_visited_items_ids_of():
    """
    get_visited_items_ids_of() returns the ids of the items viewed
    by the user BUT without specific access configuration (like public ones)
    """
    user = factories.UserFactory()
    other = factories.UserFactory()
    anonymous = AnonymousUser()
    queryset = models.Item.objects.all()

    assert not get_visited_items_ids_of(queryset, anonymous)
    assert not get_visited_items_ids_of(queryset, user)

    file1, file2, _ = factories.ItemFactory.create_batch(3)

    create_link = partial(models.LinkTrace.objects.create, user=user)

    create_link(item=file1)
    create_link(item=file2)

    # The third document is not visited
    assert sorted(get_visited_items_ids_of(queryset, user)) == sorted(
        [str(file1.pk), str(file2.pk)]
    )

    factories.UserItemAccessFactory(user=other, item=file1)
    factories.UserItemAccessFactory(user=user, item=file2)

    # The second document have an access for the user
    assert get_visited_items_ids_of(queryset, user) == [str(file1.pk)]


@pytest.mark.usefixtures("indexer_settings")
def test_get_visited_items_ids_of_deleted():
    """
    get_visited_items_ids_of() returns the ids of the items viewed
    by the user if they are not deleted.
    """
    user = factories.UserFactory()
    anonymous = AnonymousUser()
    queryset = models.Item.objects.all()

    assert not get_visited_items_ids_of(queryset, anonymous)
    assert not get_visited_items_ids_of(queryset, user)

    item = factories.ItemFactory()
    folder_deleted = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item_ancestor_deleted = factories.ItemFactory(parent=folder_deleted)

    create_link = partial(models.LinkTrace.objects.create, user=user)

    create_link(item=item)
    create_link(item=folder_deleted)
    create_link(item=item_ancestor_deleted)

    # The all documents are visited
    assert sorted(get_visited_items_ids_of(queryset, user)) == sorted(
        [str(item.pk), str(folder_deleted.pk), str(item_ancestor_deleted.pk)]
    )

    folder_deleted.soft_delete()

    # Only the first document is not deleted
    assert get_visited_items_ids_of(queryset, user) == [str(item.pk)]


@responses.activate
def test_services_search_indexers_search_errors(indexer_settings):
    """
    Items indexing response handling on Find API HTTP errors.
    """
    factories.ItemFactory()

    indexer_settings.SEARCH_INDEXER_QUERY_URL = (
        "http://app-find/api/v1.0/documents/search/"
    )

    responses.add(
        responses.POST,
        "http://app-find/api/v1.0/documents/search/",
        status=401,
        body=json_dumps({"message": "Authentication failed."}),
    )

    with pytest.raises(HTTPError):
        SearchIndexer().search("alpha", token="mytoken")


@patch("requests.post")
def test_services_search_indexers_search(mock_post, indexer_settings):
    """
    search() should call requests.post to SEARCH_INDEXER_QUERY_URL with the
    document ids from linktraces.
    """
    user = factories.UserFactory()
    indexer = SearchIndexer()

    mock_response = mock_post.return_value
    mock_response.raise_for_status.return_value = None  # No error

    item1, item2, _ = factories.ItemFactory.create_batch(3)

    create_link = partial(models.LinkTrace.objects.create, user=user)

    create_link(item=item1)
    create_link(item=item2)

    visited = get_visited_items_ids_of(models.Item.objects.all(), user)

    indexer.search("alpha", visited=visited, token="mytoken")

    args, kwargs = mock_post.call_args

    assert args[0] == indexer_settings.SEARCH_INDEXER_QUERY_URL

    query_data = kwargs.get("json")
    assert query_data["q"] == "alpha"
    assert sorted(query_data["visited"]) == sorted([str(item1.pk), str(item2.pk)])
    assert query_data["services"] == ["drive"]
    assert query_data["page_number"] == 1
    assert query_data["page_size"] == 50

    assert kwargs.get("headers") == {"Authorization": "Bearer mytoken"}
    assert kwargs.get("timeout") == 10
