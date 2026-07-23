"""
Test the item batch share API endpoint in drive's core app.
"""

from django.core import mail
from django.test import override_settings

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def batch_share_url(item):
    """Return the batch share url for the given item."""
    return f"/api/v1.0/items/{item.id!s}/batch-share/"


@override_settings(ALLOW_SHARE_IMPORT_FILE=False)
def test_api_item_batch_share_setting_disabled():
    """The endpoint should be rejected when the feature setting is disabled."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "contact@example.com", "role": "reader"}]},
        format="json",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.filter(item=item).count() == 1
    assert models.Invitation.objects.count() == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_anonymous():
    """Anonymous users should not be allowed to batch share an item."""
    item = factories.ItemFactory()

    response = APIClient().post(
        batch_share_url(item),
        {"rows": [{"email": "contact@example.com", "role": "reader"}]},
        format="json",
    )

    assert response.status_code == 401
    assert models.Invitation.objects.count() == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_authenticated_unrelated():
    """Users unrelated to the item should not be allowed to batch share it."""
    user = factories.UserFactory()
    item = factories.ItemFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "contact@example.com", "role": "reader"}]},
        format="json",
    )

    assert response.status_code == 403
    assert models.Invitation.objects.count() == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_batch_share_authenticated_reader_or_editor(role):
    """Readers and editors of an item should not be allowed to batch share it."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, role)])

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "contact@example.com", "role": "reader"}]},
        format="json",
    )

    assert response.status_code == 403
    assert models.Invitation.objects.count() == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_api_item_batch_share_privileged_mixed_rows(role, settings):
    """
    Administrators and owners should be able to batch share an item. Emails
    matching an existing user get an access, unknown emails get an invitation,
    and every created share triggers a notification email.
    """
    user = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory(users=[(user, role)])
    existing_user = factories.UserFactory(email="alice@example.com")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {
            "rows": [
                {"email": "alice@example.com", "role": "editor"},
                {"email": "bob@example.com", "role": "reader"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "accesses_created": 1,
        "invitations_created": 1,
        "skipped": [],
    }
    assert models.ItemAccess.objects.filter(item=item, user=existing_user, role="editor").exists()
    assert models.Invitation.objects.filter(
        item=item, email="bob@example.com", role="reader", issuer=user
    ).exists()
    assert len(mail.outbox) == 2
    assert sorted(email.to[0] for email in mail.outbox) == [
        "alice@example.com",
        "bob@example.com",
    ]


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_user_email_case_insensitive():
    """Emails should match existing users regardless of their case."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    existing_user = factories.UserFactory(email="Alice@Example.com")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "alice@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["accesses_created"] == 1
    assert models.ItemAccess.objects.filter(item=item, user=existing_user).exists()
    assert models.Invitation.objects.count() == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_already_shared():
    """Users already having an access with an equal or higher role should be skipped."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    shared_user = factories.UserFactory(email="alice@example.com")
    factories.UserItemAccessFactory(item=item, user=shared_user, role="editor")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "alice@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "accesses_created": 0,
        "invitations_created": 0,
        "skipped": [{"email": "alice@example.com", "reason": "already_shared"}],
    }
    assert models.ItemAccess.objects.filter(item=item, user=shared_user).count() == 1
    assert len(mail.outbox) == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_inherited_access():
    """
    Users with an inherited role higher or equal to the requested one should be
    skipped while a higher requested role creates an explicit access.
    """
    user = factories.UserFactory()
    parent = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    editor = factories.UserFactory(email="editor@example.com")
    reader = factories.UserFactory(email="reader@example.com")
    factories.UserItemAccessFactory(item=parent, user=editor, role="editor")
    factories.UserItemAccessFactory(item=parent, user=reader, role="reader")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {
            "rows": [
                {"email": "editor@example.com", "role": "reader"},
                {"email": "reader@example.com", "role": "editor"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "accesses_created": 1,
        "invitations_created": 0,
        "skipped": [{"email": "editor@example.com", "reason": "already_shared"}],
    }
    assert models.ItemAccess.objects.filter(item=item, user=reader, role="editor").exists()
    assert not models.ItemAccess.objects.filter(item=item, user=editor).exists()


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_already_invited():
    """Emails already invited to the item should be skipped."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    factories.InvitationFactory(item=item, email="bob@example.com", role="reader")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "bob@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "accesses_created": 0,
        "invitations_created": 0,
        "skipped": [{"email": "bob@example.com", "reason": "already_invited"}],
    }
    assert models.Invitation.objects.filter(item=item).count() == 1
    assert len(mail.outbox) == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_duplicated_rows():
    """Duplicated emails in the payload should only create one share."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {
            "rows": [
                {"email": "bob@example.com", "role": "editor"},
                {"email": "Bob@example.com", "role": "reader"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["invitations_created"] == 1
    assert (
        models.Invitation.objects.filter(item=item, email="bob@example.com", role="editor").count()
        == 1
    )
    assert len(mail.outbox) == 1


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_administrator_cannot_grant_owner():
    """
    An administrator should not be allowed to grant a role higher than their
    own and no row of the batch should be created in that case.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "administrator")])

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {
            "rows": [
                {"email": "bob@example.com", "role": "reader"},
                {"email": "carol@example.com", "role": "owner"},
            ]
        },
        format="json",
    )

    assert response.status_code == 403
    assert models.Invitation.objects.count() == 0
    assert len(mail.outbox) == 0


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_owner_can_grant_owner():
    """Owners should be allowed to grant the owner role."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "bob@example.com", "role": "owner"}]},
        format="json",
    )

    assert response.status_code == 200
    assert models.Invitation.objects.filter(item=item, role="owner").count() == 1


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"email": "not-an-email", "role": "reader"}],
        [{"email": "bob@example.com", "role": "unknown-role"}],
        [{"email": "bob@example.com"}],
        [{"email": f"contact{index}@example.com", "role": "reader"} for index in range(101)],
    ],
)
def test_api_item_batch_share_invalid_payload(rows):
    """Invalid payloads should be rejected without creating anything."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    client = APIClient()
    client.force_login(user)

    response = client.post(batch_share_url(item), {"rows": rows}, format="json")

    assert response.status_code == 400
    assert models.Invitation.objects.count() == 0
    assert models.ItemAccess.objects.filter(item=item).count() == 1


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_synchronizes_descendants():
    """
    Explicit accesses on descendants with a role lower or equal to the new one
    should be removed like when creating a single access.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FOLDER)
    shared_user = factories.UserFactory(email="alice@example.com")
    factories.UserItemAccessFactory(item=child, user=shared_user, role="reader")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "alice@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert models.ItemAccess.objects.filter(item=item, user=shared_user, role="editor").exists()
    assert not models.ItemAccess.objects.filter(item=child, user=shared_user).exists()
