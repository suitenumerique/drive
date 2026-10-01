"""Tests for the database migrations."""

from django.db import connection

import pytest

pytestmark = pytest.mark.django_db


def test_migrations_dropped_redundant_user_indexes():
    """Only the unique constraints on (user, item) still index the user column.

    Migration 0031 drops the single-column user indexes by their Django-generated
    names, with IF EXISTS: a renamed index would make the drop a silent no-op.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename IN ('drive_item_favorite', 'drive_link_trace')"
        )
        definitions = [row[0] for row in cursor.fetchall()]
    assert definitions, "Expected at least the unique constraints on these tables"
    for definition in definitions:
        if "user_id" in definition:
            assert "item_id" in definition, (
                f"Redundant single-column user index survived migration 0031: {definition}"
            )
