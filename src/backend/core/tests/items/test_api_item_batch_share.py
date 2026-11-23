"""
Test the item batch share API endpoint in drive's core app.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.db import transaction
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
def test_api_item_batch_share_user_email_non_ascii():
    """An email differing from an existing user's by a non-ASCII letter should be invited."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    factories.UserFactory(email="alice@example.com")

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "alıce@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["accesses_created"] == 0
    assert response.json()["invitations_created"] == 1
    assert models.Invitation.objects.filter(email="alıce@example.com", item=item).exists()


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_user_email_shared_with_inactive_user():
    """The active user should get the access when an inactive user shares the email."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    active_user = factories.UserFactory(email="alice@example.com")
    inactive_user = factories.UserFactory(email="alice@example.com", is_active=False)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "alice@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["accesses_created"] == 1
    assert models.ItemAccess.objects.filter(item=item, user=active_user).exists()
    assert not models.ItemAccess.objects.filter(item=item, user=inactive_user).exists()


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


@override_settings(ALLOW_SHARE_IMPORT_FILE=True, SHARE_IMPORT_FILE_MAX_ROWS=2)
@pytest.mark.parametrize("row_count, expected_status", [(2, 200), (3, 400)])
def test_api_item_batch_share_max_rows(row_count, expected_status):
    """Batches larger than the configured max rows should be rejected."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    client = APIClient()
    client.force_login(user)

    rows = [
        {"email": f"contact{index}@example.com", "role": "reader"} for index in range(row_count)
    ]
    response = client.post(batch_share_url(item), {"rows": rows}, format="json")

    assert response.status_code == expected_status
    expected_invitations = row_count if expected_status == 200 else 0
    assert models.Invitation.objects.count() == expected_invitations


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_default_max_rows():
    """Batches should be limited to 500 rows by default."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    client = APIClient()
    client.force_login(user)

    rows = [{"email": f"contact{index}@example.com", "role": "reader"} for index in range(501)]
    response = client.post(batch_share_url(item), {"rows": rows}, format="json")

    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "rows",
                "code": "batch_share_too_many_rows",
                "detail": "Ensure this field has no more than 500 rows.",
            }
        ],
    }
    assert models.Invitation.objects.count() == 0


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


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
@pytest.mark.parametrize(
    "users_count, expected_queries, expected_cache_calls",
    [(1, 11, 1), (20, 11, 1), (500, 11, 1)],
)
def test_api_item_batch_share_cost(
    users_count, expected_queries, expected_cache_calls, django_assert_num_queries
):
    """
    Sharing a folder of 3 items with 1, 20 or 500 users should run the pinned
    number of queries and cache invalidation calls.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=child)
    rows = [
        {"email": f"contact{index}@example.com", "role": "reader"} for index in range(users_count)
    ]
    for row in rows:
        factories.UserFactory(email=row["email"])

    client = APIClient()
    client.force_login(user)

    with (
        mock.patch.object(cache, "delete") as cache_delete,
        mock.patch.object(cache, "delete_many") as cache_delete_many,
        django_assert_num_queries(expected_queries),
    ):
        response = client.post(batch_share_url(item), {"rows": rows}, format="json")

    assert response.status_code == 200
    assert response.json()["accesses_created"] == users_count
    assert cache_delete.call_count + cache_delete_many.call_count == expected_cache_calls


@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_invalidates_nb_accesses_cache():
    """The nb_accesses cache of the item and its descendants should be invalidated."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=item)
    factories.UserFactory(email="alice@example.com")

    client = APIClient()
    client.force_login(user)

    # Warm the cache for both items
    assert item.nb_accesses == 1
    assert child.nb_accesses == 1

    response = client.post(
        batch_share_url(item),
        {"rows": [{"email": "alice@example.com", "role": "editor"}]},
        format="json",
    )

    assert response.status_code == 200
    assert cache.get(item.get_nb_accesses_cache_key()) is None
    assert cache.get(child.get_nb_accesses_cache_key()) is None


@pytest.mark.django_db(transaction=True)
@override_settings(ALLOW_SHARE_IMPORT_FILE=True)
def test_api_item_batch_share_concurrent():
    """A batch share should wait for a running one and skip the shares it created."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    shared_user = factories.UserFactory(email="alice@example.com")

    def batch_share():
        client = APIClient()
        client.force_login(user)
        return client.post(
            batch_share_url(item),
            {"rows": [{"email": "alice@example.com", "role": "reader"}]},
            format="json",
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        # Act as a running batch share: the item is locked and the access not committed
        with transaction.atomic():
            models.Item.objects.select_for_update(no_key=True).get(pk=item.pk)
            models.ItemAccess.objects.create(item=item, user=shared_user, role="reader")
            future = executor.submit(batch_share)
            time.sleep(0.5)
        response = future.result()

    assert response.status_code == 200
    assert response.json() == {
        "accesses_created": 0,
        "invitations_created": 0,
        "skipped": [{"email": "alice@example.com", "reason": "already_shared"}],
    }
