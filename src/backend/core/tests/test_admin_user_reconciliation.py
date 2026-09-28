"""Tests for the user reconciliation admin classes."""

from pathlib import Path

from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.base import ContentFile
from django.test import RequestFactory

import pytest

from core import factories, models
from core.admin import UserReconciliationCsvImportAdmin, process_reconciliation

pytestmark = pytest.mark.django_db

DATA_DIR = Path(__file__).parent / "data"


def _request_with_messages():
    """Build a request carrying a session and the messages framework."""
    request = RequestFactory().post("/")
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)  # pylint: disable=protected-access
    return request


def test_admin_process_reconciliation_processes_ready_entry():
    """The action processes entries that are ready with both emails checked."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item = factories.ItemFactory(creator=inactive)
    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email,
        inactive_email=inactive.email,
        active_email_checked=True,
        inactive_email_checked=True,
    )

    process_reconciliation(None, None, models.UserReconciliation.objects.all())

    reconciliation.refresh_from_db()
    item.refresh_from_db()
    assert reconciliation.status == "done"
    assert item.creator == active


def test_admin_process_reconciliation_skips_unconfirmed_entry():
    """The action ignores entries whose emails are not both checked."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email,
        inactive_email=inactive.email,
        active_email_checked=True,
        inactive_email_checked=False,
    )

    process_reconciliation(None, None, models.UserReconciliation.objects.all())

    reconciliation.refresh_from_db()
    assert reconciliation.status == "ready"


def test_admin_csv_import_save_model_defers_job_to_commit(django_capture_on_commit_callbacks):
    """Saving a new CSV import schedules the job on transaction commit."""
    for email in ["active1", "inactive1", "active2", "inactive2"]:
        factories.UserFactory(email=f"{email}@example.com")

    with open(DATA_DIR / "example_reconciliation_basic.csv", "rb") as file:
        csv_file = ContentFile(file.read(), name="example_reconciliation_basic.csv")
    obj = models.UserReconciliationCsvImport(file=csv_file)

    admin_instance = UserReconciliationCsvImportAdmin(
        models.UserReconciliationCsvImport, AdminSite()
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        admin_instance.save_model(_request_with_messages(), obj, None, change=False)

    # The job is deferred to commit, not run inline
    assert len(callbacks) == 1
    assert models.UserReconciliation.objects.count() == 2
