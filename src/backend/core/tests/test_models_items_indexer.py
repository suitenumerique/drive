"""
Unit tests for the item model
"""
# pylint: disable=too-many-lines

from operator import itemgetter
from unittest import mock

from django.core.cache import cache
from django.db import transaction

import pytest

from core import factories, models
from core.services.search_indexers import SearchIndexer
from core.tasks.search import file_indexer_task

pytestmark = pytest.mark.django_db


def reset_batch_indexer_throttle():
    """Reset throttle flag"""
    cache.delete("file-batch-indexer-throttle")


@pytest.fixture(autouse=True)
def reset_throttle():
    """Reset throttle flag before each test"""
    reset_batch_indexer_throttle()
    yield
    reset_batch_indexer_throttle()


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
def test_models_items_post_save_indexer():
    """Test indexation task on item creation"""
    accesses = {}

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        with transaction.atomic():
            item1, item2, item3 = factories.ItemFactory.create_batch(3)

    indexer = SearchIndexer()
    data = [call.args[0] for call in mock_push.call_args_list]

    assert len(data) == 1

    # One call
    assert sorted(data[0], key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(item1, accesses),
            indexer.serialize_item(item2, accesses),
            indexer.serialize_item(item3, accesses),
        ],
        key=itemgetter("id"),
    )

    # The throttle counters should be reset
    assert cache.get("file-batch-indexer-throttle") == 1


@pytest.mark.django_db(transaction=True)
def test_models_items_post_save_indexer_no_batches(indexer_settings):
    """Test indexation task on item creation, no throttle"""
    indexer_settings.SEARCH_INDEXER_COUNTDOWN = 0

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        with transaction.atomic():
            item1, item2, item3 = factories.ItemFactory.create_batch(3)

    accesses = {}
    data = [call.args[0] for call in mock_push.call_args_list]

    indexer = SearchIndexer()

    # 3 calls
    assert len(data) == 3
    assert sorted(data, key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(item1, accesses),
            indexer.serialize_item(item2, accesses),
            indexer.serialize_item(item3, accesses),
        ],
        key=itemgetter("id"),
    )

    # The throttle counters should be reset
    assert cache.get("file-batch-indexer-throttle") is None


@mock.patch.object(SearchIndexer, "push")
@pytest.mark.django_db(transaction=True)
def test_models_items_post_save_indexer_not_configured(mock_push, indexer_settings):
    """Task should not start an indexation when disabled"""
    indexer_settings.SEARCH_INDEXER_CLASS = None

    user = factories.UserFactory()

    with transaction.atomic():
        item = factories.ItemFactory()
        factories.UserItemAccessFactory(item=item, user=user)

    assert mock_push.assert_not_called


@pytest.mark.django_db(transaction=True)
def test_models_items_post_save_indexer_wrongly_configured(indexer_settings):
    """Task should not start an indexation when disabled"""
    indexer_settings.SEARCH_INDEXER_URL = None

    user = factories.UserFactory()

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        with transaction.atomic():
            item = factories.ItemFactory()
            factories.UserItemAccessFactory(item=item, user=user)

    assert mock_push.assert_not_called


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
def test_models_items_post_save_indexer_with_accesses():
    """Test indexation task on Item creation"""
    user = factories.UserFactory()

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        with transaction.atomic():
            item1, item2, item3 = factories.ItemFactory.create_batch(3)

            factories.UserItemAccessFactory(item=item1, user=user)
            factories.UserItemAccessFactory(item=item2, user=user)
            factories.UserItemAccessFactory(item=item3, user=user)

    accesses = {
        str(item1.path): {"users": [user.sub]},
        str(item2.path): {"users": [user.sub]},
        str(item3.path): {"users": [user.sub]},
    }

    data = [call.args[0] for call in mock_push.call_args_list]

    indexer = SearchIndexer()

    assert len(data) == 1
    assert sorted(data[0], key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(item1, accesses),
            indexer.serialize_item(item2, accesses),
            indexer.serialize_item(item3, accesses),
        ],
        key=itemgetter("id"),
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
@mock.patch.object(SearchIndexer, "push")
def test_models_items_post_save_indexer_deleted(mock_push):
    """Indexation task on deleted or ancestor_deleted Items"""
    user = factories.UserFactory()

    with transaction.atomic():
        item = factories.ItemFactory(link_reach=models.LinkReachChoices.AUTHENTICATED)
        folder = factories.ItemFactory(
            link_reach=models.LinkReachChoices.AUTHENTICATED,
            type=models.ItemTypeChoices.FOLDER,
        )
        folder_item = factories.ItemFactory(
            parent=folder,
            link_reach=models.LinkReachChoices.AUTHENTICATED,
        )

        factories.UserItemAccessFactory(item=item, user=user)
        factories.UserItemAccessFactory(item=folder, user=user)
        factories.UserItemAccessFactory(item=folder_item, user=user)

    # Manually reset the throttle flag here or the next indexation will be ignored for 1 second
    reset_batch_indexer_throttle()

    with transaction.atomic():
        folder_deleted = models.Item.objects.get(pk=folder.pk)
        folder_deleted.soft_delete()

    ancestor_deleted = models.Item.objects.get(pk=folder_item.pk)

    assert folder_deleted.deleted_at is not None
    assert folder_deleted.ancestors_deleted_at is not None

    assert ancestor_deleted.deleted_at is None
    assert ancestor_deleted.ancestors_deleted_at is not None

    accesses = {
        str(item.path): {"users": [user.sub]},
        str(folder_deleted.path): {"users": [user.sub]},
        str(ancestor_deleted.path): {"users": [user.sub]},
    }

    data = [call.args[0] for call in mock_push.call_args_list]

    indexer = SearchIndexer()

    assert len(data) == 2

    # First indexation on items creation
    assert sorted(data[0], key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(item, accesses),
            indexer.serialize_item(folder, accesses),
            indexer.serialize_item(folder_item, accesses),
        ],
        key=itemgetter("id"),
    )

    # Even deleted items are re-indexed : only update their status in the future
    assert sorted(data[1], key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(folder_deleted, accesses),  # soft_delete()
            indexer.serialize_item(ancestor_deleted, accesses),
        ],
        key=itemgetter("id"),
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
def test_models_items_indexer_hard_deleted():
    """Indexation task on hard deleted Item"""
    user = factories.UserFactory()

    with transaction.atomic():
        item = factories.ItemFactory(link_reach=models.LinkReachChoices.AUTHENTICATED)
        factories.UserItemAccessFactory(item=item, user=user)

    doc_id = item.pk

    item.soft_delete()
    item.delete()

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        # Call task on deleted Item.
        file_indexer_task.apply(args=[doc_id])

    # Hard delete Item are not re-indexed.
    assert mock_push.assert_not_called


@mock.patch.object(SearchIndexer, "push")
@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
def test_models_items_post_save_indexer_restored(mock_push):
    """Restart indexation task on restored Items"""
    user = factories.UserFactory()

    with transaction.atomic():
        item = factories.ItemFactory(link_reach=models.LinkReachChoices.AUTHENTICATED)
        folder_deleted = factories.ItemFactory(
            link_reach=models.LinkReachChoices.AUTHENTICATED,
            type=models.ItemTypeChoices.FOLDER,
        )
        ancestor_deleted = factories.ItemFactory(
            parent=folder_deleted,
            link_reach=models.LinkReachChoices.AUTHENTICATED,
        )

        factories.UserItemAccessFactory(item=item, user=user)
        factories.UserItemAccessFactory(item=folder_deleted, user=user)
        factories.UserItemAccessFactory(item=ancestor_deleted, user=user)

        folder_deleted.soft_delete()

    folder_deleted.refresh_from_db()
    ancestor_deleted.refresh_from_db()

    assert folder_deleted.deleted_at is not None
    assert folder_deleted.ancestors_deleted_at is not None

    assert ancestor_deleted.deleted_at is None
    assert ancestor_deleted.ancestors_deleted_at is not None

    # Manually reset the throttle flag here or the next indexation will be ignored for 1 second
    reset_batch_indexer_throttle()

    with transaction.atomic():
        folder_restored = models.Item.objects.get(pk=folder_deleted.pk)
        folder_restored.restore()

    ancestor_restored = models.Item.objects.get(pk=ancestor_deleted.pk)

    assert folder_restored.deleted_at is None
    assert folder_restored.ancestors_deleted_at is None

    assert ancestor_restored.deleted_at is None
    assert ancestor_restored.ancestors_deleted_at is None

    accesses = {
        str(item.path): {"users": [user.sub]},
        str(folder_deleted.path): {"users": [user.sub]},
        str(ancestor_deleted.path): {"users": [user.sub]},
    }

    data = [call.args[0] for call in mock_push.call_args_list]

    indexer = SearchIndexer()

    # All docs are re-indexed
    assert len(data) == 2

    # First indexation on items creation & soft delete (in the same transaction)
    assert sorted(data[0], key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(item, accesses),
            indexer.serialize_item(folder_deleted, accesses),
            indexer.serialize_item(ancestor_deleted, accesses),
        ],
        key=itemgetter("id"),
    )

    # Restored items are re-indexed : only update their status in the future
    assert sorted(data[1], key=itemgetter("id")) == sorted(
        [
            indexer.serialize_item(folder_restored, accesses),  # restore()
            indexer.serialize_item(ancestor_restored, accesses),
        ],
        key=itemgetter("id"),
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
def test_models_items_post_save_indexer_throttle():
    """Test indexation task skipping on Item update"""
    indexer = SearchIndexer()
    user = factories.UserFactory()

    with mock.patch.object(SearchIndexer, "push"):
        with transaction.atomic():
            items = factories.ItemFactory.create_batch(5, users=(user,))

    accesses = {str(item.path): {"users": [user.sub]} for item in items}

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        # Simulate 1 running task
        cache.set("file-batch-indexer-throttle", 1)

        # save item to trigger the indexer, but nothing should be done since
        # the flag is up
        with transaction.atomic():
            items[0].save()
            items[2].save()
            items[3].save()

        assert [call.args[0] for call in mock_push.call_args_list] == []

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        # No waiting task
        cache.delete("file-batch-indexer-throttle")

        with transaction.atomic():
            items[0].save()
            items[2].save()
            items[3].save()

        data = [call.args[0] for call in mock_push.call_args_list]

        # One call
        assert len(data) == 1

        assert sorted(data[0], key=itemgetter("id")) == sorted(
            [
                indexer.serialize_item(items[0], accesses),
                indexer.serialize_item(items[2], accesses),
                indexer.serialize_item(items[3], accesses),
            ],
            key=itemgetter("id"),
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("indexer_settings")
def test_models_items_access_post_save_indexer():
    """Test indexation task on ItemAccess update"""
    users = factories.UserFactory.create_batch(3)

    with transaction.atomic():
        item = factories.ItemFactory(users=users)
        item_accesses = models.ItemAccess.objects.filter(item=item).order_by(
            "user__sub"
        )

    reset_batch_indexer_throttle()

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        with transaction.atomic():
            for item_access in item_accesses:
                item_access.save()

        data = [call.args[0] for call in mock_push.call_args_list]

        # One call
        assert len(data) == 1

        assert [d["id"] for d in data[0]] == [str(item.pk)]


@pytest.mark.django_db(transaction=True)
def test_models_items_access_post_save_indexer_no_throttle(indexer_settings):
    """Test indexation task on ItemAccess update, no throttle"""
    indexer_settings.SEARCH_INDEXER_COUNTDOWN = 0

    users = factories.UserFactory.create_batch(3)

    with transaction.atomic():
        item = factories.ItemFactory(users=users)
        item_accesses = models.ItemAccess.objects.filter(item=item).order_by(
            "user__sub"
        )

    reset_batch_indexer_throttle()

    with mock.patch.object(SearchIndexer, "push") as mock_push:
        with transaction.atomic():
            for item_access in item_accesses:
                item_access.save()

        data = [call.args[0] for call in mock_push.call_args_list]

        # 3 calls
        assert len(data) == 3
        assert [d["id"] for d in data] == [str(item.pk)] * 3
