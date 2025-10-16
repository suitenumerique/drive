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

from core import factories, models, utils
from core.services.search_indexers import (
    BaseItemIndexer,
    SearchIndexer,
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


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_item_textfile():
    """
    It should serialize documents with correct metadata and access control.
    """
    user_a, user_b = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(
        upload_bytes=b"This is a text file content",
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
        "depth": 1,
        "path": str(item.path),
        "numchild": 0,
        "mimetype": "text/plain",
        "content": "This is a text file content",
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "reach": item.link_reach,
        "size": item.size,
        "is_active": True,
        "is_extracted": True,
        "is_too_big": False,
    }


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_item_file():
    """
    It should serialize documents with correct metadata and access control.
    """
    user_a, user_b = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(
        upload_bytes=b"This is a text file content", mimetype="application/pdf"
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
    It should serialize documents with correct metadata and access control.
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
        "title": f"{folder.title}\nAny description",
        "depth": 1,
        "path": str(folder.path),
        "numchild": 0,
        "mimetype": "text/plain",
        "content": "",
        "created_at": folder.created_at.isoformat(),
        "updated_at": folder.updated_at.isoformat(),
        "reach": folder.link_reach,
        "size": folder.size,
        "is_active": True,
    }


@pytest.mark.usefixtures("indexer_settings")
def test_services_search_indexers_serialize_item_textfile():
    """
    It should serialize documents with correct metadata and access control.
    """
    user_a, user_b = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(
        upload_bytes=b"This is a text file content",
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
    item = factories.ItemFactory(parent=folder, mimetype="text/plain")

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
    factories.ItemFactory(mimetype="text/plain")

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
        upload_state=models.ItemUploadStateChoices.READY,
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
def test_services_search_indexers_ignore_not_ready(mock_push):
    """
    File indexing should be processed in batches,
    and only the access data relevant to each batch should be used.
    """
    item = factories.ItemFactory(
        mimetype="text/plain",
        upload_state=models.ItemUploadStateChoices.READY,
    )

    # wrong mimetype
    pdf_item = factories.ItemFactory(
        mimetype="application/pdf",
        upload_state=models.ItemUploadStateChoices.READY,
    )

    # not ready
    factories.ItemFactory.create_batch(
        5,
        upload_state=fuzzy.FuzzyChoice(
            [
                models.ItemUploadStateChoices.PENDING,
                models.ItemUploadStateChoices.ANALYZING,
                models.ItemUploadStateChoices.SUSPICIOUS,
                models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE,
            ]
        ),
    )

    assert SearchIndexer().index() == 2

    assert mock_push.call_count == 1

    results = {item["id"] for item in mock_push.call_args[0][0]}
    assert results == {
        str(item.id),
        str(pdf_item.id),
    }


# TODO finish tests

# @patch.object(SearchIndexer, "push")
# @pytest.mark.usefixtures("indexer_settings")
# def test_services_search_indexers_ancestors_link_reach(mock_push):
#     """Document accesses and reach should take into account ancestors link reaches."""
#     great_grand_parent = factories.DocumentFactory(link_reach="restricted")
#     grand_parent = factories.DocumentFactory(
#         parent=great_grand_parent, link_reach="authenticated"
#     )
#     parent = factories.DocumentFactory(parent=grand_parent, link_reach="public")
#     document = factories.DocumentFactory(parent=parent, link_reach="restricted")

#     assert SearchIndexer().index() == 4

#     results = {doc["id"]: doc for doc in mock_push.call_args[0][0]}
#     assert len(results) == 4
#     assert results[str(great_grand_parent.id)]["reach"] == "restricted"
#     assert results[str(grand_parent.id)]["reach"] == "authenticated"
#     assert results[str(parent.id)]["reach"] == "public"
#     assert results[str(document.id)]["reach"] == "public"


# @patch.object(SearchIndexer, "push")
# @pytest.mark.usefixtures("indexer_settings")
# def test_services_search_indexers_ancestors_users(mock_push):
#     """Document accesses and reach should include users from ancestors."""
#     user_gp, user_p, user_d = factories.UserFactory.create_batch(3)

#     grand_parent = factories.DocumentFactory(users=[user_gp])
#     parent = factories.DocumentFactory(parent=grand_parent, users=[user_p])
#     document = factories.DocumentFactory(parent=parent, users=[user_d])

#     assert SearchIndexer().index() == 3

#     results = {doc["id"]: doc for doc in mock_push.call_args[0][0]}
#     assert len(results) == 3
#     assert results[str(grand_parent.id)]["users"] == [str(user_gp.sub)]
#     assert set(results[str(parent.id)]["users"]) == {str(user_gp.sub), str(user_p.sub)}
#     assert set(results[str(document.id)]["users"]) == {
#         str(user_gp.sub),
#         str(user_p.sub),
#         str(user_d.sub),
#     }


# @patch.object(SearchIndexer, "push")
# @pytest.mark.usefixtures("indexer_settings")
# def test_services_search_indexers_ancestors_teams(mock_push):
#     """Document accesses and reach should include teams from ancestors."""
#     grand_parent = factories.DocumentFactory(teams=["team_gp"])
#     parent = factories.DocumentFactory(parent=grand_parent, teams=["team_p"])
#     document = factories.DocumentFactory(parent=parent, teams=["team_d"])

#     assert SearchIndexer().index() == 3

#     results = {doc["id"]: doc for doc in mock_push.call_args[0][0]}
#     assert len(results) == 3
#     assert results[str(grand_parent.id)]["groups"] == ["team_gp"]
#     assert set(results[str(parent.id)]["groups"]) == {"team_gp", "team_p"}
#     assert set(results[str(document.id)]["groups"]) == {"team_gp", "team_p", "team_d"}


# @patch("requests.post")
# def test_push_uses_correct_url_and_data(mock_post, indexer_settings):
#     """
#     push() should call requests.post with the correct URL from settings
#     the timeout set to 10 seconds and the data as JSON.
#     """
#     indexer_settings.SEARCH_INDEXER_URL = "http://example.com/index"

#     indexer = SearchIndexer()
#     sample_data = [{"id": "123", "title": "Test"}]

#     mock_response = mock_post.return_value
#     mock_response.raise_for_status.return_value = None  # No error

#     indexer.push(sample_data)

#     mock_post.assert_called_once()
#     args, kwargs = mock_post.call_args

#     assert args[0] == indexer_settings.SEARCH_INDEXER_URL
#     assert kwargs.get("json") == sample_data
#     assert kwargs.get("timeout") == 10


# def test_get_visited_document_ids_of():
#     """
#     get_visited_document_ids_of() returns the ids of the documents viewed
#     by the user BUT without specific access configuration (like public ones)
#     """
#     user = factories.UserFactory()
#     other = factories.UserFactory()
#     anonymous = AnonymousUser()
#     queryset = models.Document.objects.all()

#     assert not get_visited_document_ids_of(queryset, anonymous)
#     assert not get_visited_document_ids_of(queryset, user)

#     doc1, doc2, _ = factories.DocumentFactory.create_batch(3)

#     create_link = partial(models.LinkTrace.objects.create, user=user, is_masked=False)

#     create_link(document=doc1)
#     create_link(document=doc2)

#     # The third document is not visited
#     assert sorted(get_visited_document_ids_of(queryset, user)) == sorted(
#         [str(doc1.pk), str(doc2.pk)]
#     )

#     factories.UserDocumentAccessFactory(user=other, document=doc1)
#     factories.UserDocumentAccessFactory(user=user, document=doc2)

#     # The second document have an access for the user
#     assert get_visited_document_ids_of(queryset, user) == [str(doc1.pk)]


# @pytest.mark.usefixtures("indexer_settings")
# def test_get_visited_document_ids_of_deleted():
#     """
#     get_visited_document_ids_of() returns the ids of the documents viewed
#     by the user if they are not deleted.
#     """
#     user = factories.UserFactory()
#     anonymous = AnonymousUser()
#     queryset = models.Document.objects.all()

#     assert not get_visited_document_ids_of(queryset, anonymous)
#     assert not get_visited_document_ids_of(queryset, user)

#     doc = factories.DocumentFactory()
#     doc_deleted = factories.DocumentFactory()
#     doc_ancestor_deleted = factories.DocumentFactory(parent=doc_deleted)

#     create_link = partial(models.LinkTrace.objects.create, user=user, is_masked=False)

#     create_link(document=doc)
#     create_link(document=doc_deleted)
#     create_link(document=doc_ancestor_deleted)

#     # The all documents are visited
#     assert sorted(get_visited_document_ids_of(queryset, user)) == sorted(
#         [str(doc.pk), str(doc_deleted.pk), str(doc_ancestor_deleted.pk)]
#     )

#     doc_deleted.soft_delete()

#     # Only the first document is not deleted
#     assert get_visited_document_ids_of(queryset, user) == [str(doc.pk)]


# @responses.activate
# def test_services_search_indexers_search_errors(indexer_settings):
#     """
#     Documents indexing response handling on Find API HTTP errors.
#     """
#     factories.DocumentFactory()

#     indexer_settings.SEARCH_INDEXER_QUERY_URL = (
#         "http://app-find/api/v1.0/documents/search/"
#     )

#     responses.add(
#         responses.POST,
#         "http://app-find/api/v1.0/documents/search/",
#         status=401,
#         body=json_dumps({"message": "Authentication failed."}),
#     )

#     with pytest.raises(HTTPError):
#         SearchIndexer().search("alpha", token="mytoken")


# @patch("requests.post")
# def test_services_search_indexers_search(mock_post, indexer_settings):
#     """
#     search() should call requests.post to SEARCH_INDEXER_QUERY_URL with the
#     document ids from linktraces.
#     """
#     user = factories.UserFactory()
#     indexer = SearchIndexer()

#     mock_response = mock_post.return_value
#     mock_response.raise_for_status.return_value = None  # No error

#     doc1, doc2, _ = factories.DocumentFactory.create_batch(3)

#     create_link = partial(models.LinkTrace.objects.create, user=user, is_masked=False)

#     create_link(document=doc1)
#     create_link(document=doc2)

#     visited = get_visited_document_ids_of(models.Document.objects.all(), user)

#     indexer.search("alpha", visited=visited, token="mytoken")

#     args, kwargs = mock_post.call_args

#     assert args[0] == indexer_settings.SEARCH_INDEXER_QUERY_URL

#     query_data = kwargs.get("json")
#     assert query_data["q"] == "alpha"
#     assert sorted(query_data["visited"]) == sorted([str(doc1.pk), str(doc2.pk)])
#     assert query_data["services"] == ["docs"]
#     assert query_data["page_number"] == 1
#     assert query_data["page_size"] == 50
#     assert query_data["order_by"] == "updated_at"
#     assert query_data["order_direction"] == "desc"

#     assert kwargs.get("headers") == {"Authorization": "Bearer mytoken"}
#     assert kwargs.get("timeout") == 10
