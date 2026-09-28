"""Tests for the ReconciliationConfirmView API view."""

import uuid

from django.conf import settings

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_reconciliation_confirm_active():
    """Confirming the active link sets active_email_checked."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email,
        inactive_email=inactive.email,
        active_user=active,
        inactive_user=inactive,
        active_email_checked=False,
        inactive_email_checked=False,
        status="ready",
    )

    url = (
        f"/api/{settings.API_VERSION}/user-reconciliations/active/"
        f"{reconciliation.active_email_confirmation_id}/"
    )
    response = APIClient().get(url)

    assert response.status_code == 200
    assert response.json() == {"detail": "Confirmation received"}

    reconciliation.refresh_from_db()
    assert reconciliation.active_email_checked is True
    assert reconciliation.inactive_email_checked is False


def test_api_reconciliation_confirm_inactive():
    """Confirming the inactive link sets inactive_email_checked."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email,
        inactive_email=inactive.email,
        active_user=active,
        inactive_user=inactive,
        active_email_checked=False,
        inactive_email_checked=False,
        status="ready",
    )

    url = (
        f"/api/{settings.API_VERSION}/user-reconciliations/inactive/"
        f"{reconciliation.inactive_email_confirmation_id}/"
    )
    response = APIClient().get(url)

    assert response.status_code == 200
    reconciliation.refresh_from_db()
    assert reconciliation.inactive_email_checked is True
    assert reconciliation.active_email_checked is False


def test_api_reconciliation_confirm_invalid_user_type():
    """An unknown user_type returns a 400."""
    url = f"/api/{settings.API_VERSION}/user-reconciliations/other/{uuid.uuid4()}/"
    response = APIClient().get(url)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid user_type"}


def test_api_reconciliation_confirm_not_found():
    """An unknown confirmation id returns a 404."""
    url = f"/api/{settings.API_VERSION}/user-reconciliations/active/{uuid.uuid4()}/"
    response = APIClient().get(url)

    assert response.status_code == 404
    assert response.json() == {"detail": "Reconciliation entry not found"}
