"""
Tests for the operations shared by the migrations
"""

from django.apps import apps
from django.db import NotSupportedError, connection, models
from django.db.migrations.state import ProjectState
from django.test.utils import CaptureQueriesContext

import pytest

from core.utils.migrations import AddIndexConcurrentlyIfMissing

INDEX_NAME = "test_utils_migrations_idx"


@pytest.fixture(name="operation")
def fixture_operation():
    """An operation indexing the title of items, its index is dropped after the test."""
    yield AddIndexConcurrentlyIfMissing(
        model_name="item",
        index=models.Index(fields=["title"], name=INDEX_NAME),
    )
    with connection.cursor() as cursor:
        cursor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")


def create_index(valid=True):
    """Create the index outside the operation, flagged invalid if requested."""
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE INDEX {INDEX_NAME} ON drive_item (title)")
        if not valid:
            # An interrupted concurrent build cannot be reproduced reliably, flag the
            # index the way it leaves it
            cursor.execute(
                "UPDATE pg_index SET indisvalid = false WHERE indexrelid = to_regclass(%s)",
                [INDEX_NAME],
            )


def index_validity():
    """Return None when the index does not exist, else whether Postgres flags it valid."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indisvalid FROM pg_index WHERE indexrelid = to_regclass(%s)",
            [INDEX_NAME],
        )
        row = cursor.fetchone()
    return row[0] if row else None


def apply(operation, atomic=False):
    """Run the operation forwards and return the statements it ran on the index."""
    state = ProjectState.from_apps(apps)

    with CaptureQueriesContext(connection) as queries:
        with connection.schema_editor(atomic=atomic) as schema_editor:
            operation.database_forwards("core", schema_editor, state, state)

    return [
        " ".join(query["sql"].split()[:3])
        for query in queries
        if INDEX_NAME in query["sql"] and " INDEX " in query["sql"]
    ]


# CREATE INDEX CONCURRENTLY cannot run inside the transaction wrapping regular tests
@pytest.mark.django_db(transaction=True)
def test_utils_migrations_add_index_concurrently_if_missing_missing(operation):
    """The index is built when it does not exist."""
    assert index_validity() is None

    assert apply(operation) == ["CREATE INDEX CONCURRENTLY"]

    assert index_validity() is True


@pytest.mark.django_db(transaction=True)
def test_utils_migrations_add_index_concurrently_if_missing_valid(operation):
    """
    The operation succeeds without building the index again when a valid one exists,
    as when it is created by hand before a release is deployed.
    """
    create_index()

    assert apply(operation) == []

    assert index_validity() is True


@pytest.mark.django_db(transaction=True)
def test_utils_migrations_add_index_concurrently_if_missing_invalid(operation):
    """
    An invalid index, as left behind by an interrupted concurrent build, is dropped and
    built again.
    """
    create_index(valid=False)

    assert apply(operation) == [
        "DROP INDEX CONCURRENTLY",
        "CREATE INDEX CONCURRENTLY",
    ]

    assert index_validity() is True


@pytest.mark.django_db
def test_utils_migrations_add_index_concurrently_if_missing_in_transaction(operation):
    """
    Dropping an invalid index concurrently is refused inside a transaction, before any
    statement is sent.
    """
    create_index(valid=False)

    with pytest.raises(NotSupportedError, match="set atomic = False"):
        apply(operation, atomic=True)

    assert index_validity() is False
