"""Tests for the user reconciliation CSV import task."""

import logging
import uuid
from pathlib import Path

from django.core import mail
from django.core.files.base import ContentFile

import pytest

from core import factories, models
from core.tasks.user_reconciliation import user_reconciliation_csv_import_job

pytestmark = pytest.mark.django_db

DATA_DIR = Path(__file__).parent.parent / "data"


def make_import(filename):
    """Create a UserReconciliationCsvImport from a fixture CSV file."""
    with open(DATA_DIR / filename, "rb") as file:
        csv_file = ContentFile(file.read(), name=filename)
    return models.UserReconciliationCsvImport.objects.create(file=csv_file)


def test_user_reconciliation_csv_import_missing_job(caplog):
    """A missing import job logs a warning and returns without raising."""
    with caplog.at_level(logging.WARNING):
        user_reconciliation_csv_import_job(uuid.uuid4())

    assert "no longer exists" in caplog.text


def test_user_reconciliation_csv_import_creates_entries():
    """A well-formed CSV creates one reconciliation entry per row."""
    for email in ["active1", "inactive1", "active2", "inactive2"]:
        factories.UserFactory(email=f"{email}@example.com")

    csv_import = make_import("example_reconciliation_basic.csv")
    user_reconciliation_csv_import_job(csv_import.id)
    csv_import.refresh_from_db()

    assert csv_import.status == "done"
    assert models.UserReconciliation.objects.count() == 2
    assert models.UserReconciliation.objects.filter(status="ready").count() == 2


def test_user_reconciliation_csv_import_empty_file():
    """An empty CSV fails into the error status instead of hanging in running."""
    csv_import = models.UserReconciliationCsvImport.objects.create(
        file=ContentFile(b"", name="empty.csv")
    )
    user_reconciliation_csv_import_job(csv_import.id)
    csv_import.refresh_from_db()

    assert csv_import.status == "error"
    assert "missing mandatory columns" in csv_import.logs


def test_user_reconciliation_csv_import_missing_column():
    """A CSV missing a mandatory column fails into the error status."""
    csv_import = make_import("example_reconciliation_missing_column.csv")
    user_reconciliation_csv_import_job(csv_import.id)
    csv_import.refresh_from_db()

    assert csv_import.status == "error"
    assert "missing mandatory columns" in csv_import.logs
    assert models.UserReconciliation.objects.count() == 0


def test_user_reconciliation_csv_import_invalid_email():
    """An invalid email is logged and triggers an error email, without failing the job."""
    factories.UserFactory(email="active1@example.com")

    csv_import = make_import("example_reconciliation_error.csv")
    user_reconciliation_csv_import_job(csv_import.id)
    csv_import.refresh_from_db()

    assert csv_import.status == "done"
    assert "Invalid inactive email address on row 40" in csv_import.logs
    assert models.UserReconciliation.objects.count() == 0

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 1
    # pylint: disable-next=no-member
    assert mail.outbox[0].to == ["active1@example.com"]


def test_user_reconciliation_csv_import_multiple_inactive_emails():
    """A single row may list several inactive emails separated by a pipe."""
    for email in ["active1", "inactive1", "inactive2"]:
        factories.UserFactory(email=f"{email}@example.com")

    csv_import = make_import("example_reconciliation_grist_form.csv")
    user_reconciliation_csv_import_job(csv_import.id)
    csv_import.refresh_from_db()

    assert csv_import.status == "done"
    assert models.UserReconciliation.objects.count() == 2
    assert set(models.UserReconciliation.objects.values_list("inactive_email", flat=True)) == {
        "inactive1@example.com",
        "inactive2@example.com",
    }


def test_user_reconciliation_csv_import_is_idempotent():
    """Re-importing the same source ids does not create duplicate entries."""
    for email in ["active1", "inactive1", "active2", "inactive2"]:
        factories.UserFactory(email=f"{email}@example.com")

    csv_import = make_import("example_reconciliation_basic.csv")
    user_reconciliation_csv_import_job(csv_import.id)

    second_import = make_import("example_reconciliation_basic.csv")
    user_reconciliation_csv_import_job(second_import.id)
    second_import.refresh_from_db()

    assert models.UserReconciliation.objects.count() == 2
    assert "already processed" in second_import.logs
