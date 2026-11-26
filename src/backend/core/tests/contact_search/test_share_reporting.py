"""Shares made in Drive are reported to the contact search backend."""

import pytest

from core import factories, models

from .conftest import ACCESS_TOKEN, INTERACTIONS_PATH, logged_in_client

pytestmark = pytest.mark.django_db


def _owned_item(user):
    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")
    return item


def _reported(contacts):
    return [
        [entry["email"] for entry in body["items"]] for body in contacts.bodies(INTERACTIONS_PATH)
    ]


@pytest.mark.usefixtures("contacts_backend")
def test_an_access_is_reported(user, contacts, django_capture_on_commit_callbacks):
    """Sharing with a Drive user reports their address, with the user's token."""
    contacts.answer("POST", INTERACTIONS_PATH, status=204)
    item = _owned_item(user)
    bob = factories.UserFactory(email="bob@example.org")

    with django_capture_on_commit_callbacks(execute=True):
        response = logged_in_client(user).post(
            f"/api/v1.0/items/{item.id!s}/accesses/",
            {"user_id": str(bob.id), "role": "reader"},
            format="json",
        )

    assert response.status_code == 201
    assert _reported(contacts) == [["bob@example.org"]]
    assert contacts.calls[0].headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"


@pytest.mark.usefixtures("contacts_backend")
def test_an_invitation_is_reported(user, contacts, django_capture_on_commit_callbacks):
    """Inviting an address reports it."""
    contacts.answer("POST", INTERACTIONS_PATH, status=204)
    item = _owned_item(user)

    with django_capture_on_commit_callbacks(execute=True):
        response = logged_in_client(user).post(
            f"/api/v1.0/items/{item.id!s}/invitations/",
            {"email": "marie@example.org", "role": "reader"},
            format="json",
        )

    assert response.status_code == 201
    assert _reported(contacts) == [["marie@example.org"]]


@pytest.mark.usefixtures("contacts_backend")
def test_a_batch_share_is_reported_once(
    user, contacts, settings, django_capture_on_commit_callbacks
):
    """A batch share is one report with everyone in it."""
    settings.ALLOW_SHARE_IMPORT_FILE = True
    contacts.answer("POST", INTERACTIONS_PATH, status=204)
    item = _owned_item(user)
    factories.UserFactory(email="bob@example.org")

    with django_capture_on_commit_callbacks(execute=True):
        response = logged_in_client(user).post(
            f"/api/v1.0/items/{item.id!s}/batch-share/",
            {
                "rows": [
                    {"email": "bob@example.org", "role": "reader"},
                    {"email": "marie@example.org", "role": "reader"},
                ]
            },
            format="json",
        )

    assert response.status_code == 200
    assert _reported(contacts) == [["bob@example.org", "marie@example.org"]]


def test_the_local_backend_reports_nothing(user, contacts, django_capture_on_commit_callbacks):
    """By default, a share calls nobody."""
    item = _owned_item(user)

    with django_capture_on_commit_callbacks(execute=True):
        response = logged_in_client(user).post(
            f"/api/v1.0/items/{item.id!s}/invitations/",
            {"email": "marie@example.org", "role": "reader"},
            format="json",
        )

    assert response.status_code == 201
    assert not contacts.calls


@pytest.mark.usefixtures("contacts_backend")
def test_a_failed_report_doesnt_fail_the_share(user, contacts, django_capture_on_commit_callbacks):
    """The share is saved even when Contacts is down."""
    contacts.answer("POST", INTERACTIONS_PATH, status=503)
    item = _owned_item(user)

    with django_capture_on_commit_callbacks(execute=True):
        response = logged_in_client(user).post(
            f"/api/v1.0/items/{item.id!s}/invitations/",
            {"email": "marie@example.org", "role": "reader"},
            format="json",
        )

    assert response.status_code == 201
    assert models.Invitation.objects.filter(email="marie@example.org").exists()
