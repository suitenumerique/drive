"""
Unit test for `index` command.
"""

import logging
from operator import itemgetter
from unittest import mock

from django.core.management import call_command
from django.db import transaction

import pytest

from core import factories, models
from core.services.search_indexers import SearchIndexer


@pytest.mark.django_db
@pytest.mark.usefixtures("indexer_settings")
def test_index():
    """Test the command `index` that run the Find app indexer for all the available items."""
    user = factories.UserFactory()
    indexer = SearchIndexer()

    with transaction.atomic():
        item = factories.ItemFactory(
            upload_bytes=b"This is a text file content",
            mimetype="text/plain",
            type=models.ItemTypeChoices.FILE,
        )
        empty_item = factories.ItemFactory(
            mimetype="text/plain",
            type=models.ItemTypeChoices.FILE,
        )
        not_text_item = factories.ItemFactory(
            upload_bytes=b"This is a PDF file content",
            mimetype="application/pdf",
            type=models.ItemTypeChoices.FILE,
        )

        factories.UserItemAccessFactory(item=item, user=user)
        factories.UserItemAccessFactory(item=empty_item, user=user)
        factories.UserItemAccessFactory(item=not_text_item, user=user)

    accesses = {
        str(item.path): {"users": [user.sub]},
        str(empty_item.path): {"users": [user.sub]},
        str(not_text_item.path): {"users": [user.sub]},
    }

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        call_command("index")

        push_call_args = [call.args[0] for call in mock_push.call_args_list]

        # called once but with a batch of docs
        mock_push.assert_called_once()

        assert sorted(push_call_args[0], key=itemgetter("id")) == sorted(
            [
                indexer.serialize_item(item, accesses),
                indexer.serialize_item(empty_item, accesses),
                indexer.serialize_item(not_text_item, accesses),
            ],
            key=itemgetter("id"),
        )


@pytest.mark.django_db
@pytest.mark.usefixtures("indexer_settings")
def test_index_improperly_configured(indexer_settings, caplog):
    """The command should raise an exception if the indexer is not configured"""
    indexer_settings.SEARCH_INDEXER_CLASS = None

    with transaction.atomic():
        factories.ItemFactory(
            upload_bytes=b"This is a text file content",
            mimetype="text/plain",
            type=models.ItemTypeChoices.FILE,
        )

    with caplog.at_level(logging.WARN):
        with mock.patch.object(SearchIndexer, "push") as mock_push:
            call_command("index")

    mock_push.assert_not_called()

    assert "The indexer is not enabled or properly configured." in caplog.messages
