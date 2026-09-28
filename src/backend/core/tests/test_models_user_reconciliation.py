"""
Unit tests for the UserReconciliation model.
"""

from django.core import mail

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def create_reconciliation(active_user, inactive_user, **kwargs):
    """Create a ready-to-process reconciliation between two users."""
    return models.UserReconciliation.objects.create(
        active_email=active_user.email,
        inactive_email=inactive_user.email,
        active_email_checked=True,
        inactive_email_checked=True,
        **kwargs,
    )


def test_models_user_reconciliation_save_resolves_users_and_sends_emails():
    """Saving a pending reconciliation resolves users and sends confirmation emails."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")

    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email, inactive_email=inactive.email
    )

    assert reconciliation.status == "ready"
    assert reconciliation.active_user == active
    assert reconciliation.inactive_user == inactive

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 2
    # pylint: disable-next=no-member
    assert {mail.outbox[0].to[0], mail.outbox[1].to[0]} == {
        "active@example.com",
        "inactive@example.com",
    }


def test_models_user_reconciliation_save_missing_user_sets_error():
    """Saving fails into error status when one of the users does not exist."""
    active = factories.UserFactory(email="active@example.com")

    reconciliation = models.UserReconciliation.objects.create(
        active_email=active.email, inactive_email="ghost@example.com"
    )

    assert reconciliation.status == "error"
    assert "Both active and inactive users need to exist" in reconciliation.logs
    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0


def test_models_user_reconciliation_save_checked_emails_skip_confirmation():
    """No confirmation email is sent when both emails are already checked."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")

    reconciliation = create_reconciliation(active, inactive)

    assert reconciliation.status == "ready"
    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0


def test_models_user_reconciliation_transfers_item_access():
    """Accesses of the inactive user are transferred to the active user."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item = factories.ItemFactory()
    access = factories.UserItemAccessFactory(
        item=item, user=inactive, role=models.RoleChoices.EDITOR
    )

    create_reconciliation(active, inactive).process_reconciliation_request()

    access.refresh_from_db()
    assert access.user == active
    assert access.role == models.RoleChoices.EDITOR


def test_models_user_reconciliation_merges_item_access_role_on_conflict():
    """When both users have access, the higher role is kept and the duplicate removed."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item = factories.ItemFactory()
    active_access = factories.UserItemAccessFactory(
        item=item, user=active, role=models.RoleChoices.READER
    )
    inactive_access = factories.UserItemAccessFactory(
        item=item, user=inactive, role=models.RoleChoices.ADMIN
    )

    create_reconciliation(active, inactive).process_reconciliation_request()

    active_access.refresh_from_db()
    assert active_access.role == models.RoleChoices.ADMIN
    assert not models.ItemAccess.objects.filter(id=inactive_access.id).exists()


def test_models_user_reconciliation_transfers_favorites_and_dedup():
    """Favorites are transferred, duplicates on the active side are removed."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    shared_item = factories.ItemFactory()
    inactive_only_item = factories.ItemFactory()
    models.ItemFavorite.objects.create(user=active, item=shared_item)
    duplicate = models.ItemFavorite.objects.create(user=inactive, item=shared_item)
    transferred = models.ItemFavorite.objects.create(user=inactive, item=inactive_only_item)

    create_reconciliation(active, inactive).process_reconciliation_request()

    assert not models.ItemFavorite.objects.filter(id=duplicate.id).exists()
    transferred.refresh_from_db()
    assert transferred.user == active


def test_models_user_reconciliation_transfers_link_traces_and_dedup():
    """Link traces are transferred, duplicates on the active side are removed."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    shared_item = factories.ItemFactory()
    inactive_only_item = factories.ItemFactory()
    models.LinkTrace.objects.create(user=active, item=shared_item)
    duplicate = models.LinkTrace.objects.create(user=inactive, item=shared_item)
    transferred = models.LinkTrace.objects.create(user=inactive, item=inactive_only_item)

    create_reconciliation(active, inactive).process_reconciliation_request()

    assert not models.LinkTrace.objects.filter(id=duplicate.id).exists()
    transferred.refresh_from_db()
    assert transferred.user == active


def test_models_user_reconciliation_invalidates_nb_accesses_cache():
    """Removing a duplicate access must invalidate the item's nb_accesses cache."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=active, role=models.RoleChoices.READER)
    factories.UserItemAccessFactory(item=item, user=inactive, role=models.RoleChoices.ADMIN)

    # Prime the cache with the current count
    assert models.Item.objects.get(pk=item.pk).nb_accesses == 2

    create_reconciliation(active, inactive).process_reconciliation_request()

    # The inactive duplicate is removed: the cache must reflect a single access
    assert models.Item.objects.get(pk=item.pk).nb_accesses == 1


def test_models_user_reconciliation_reassigns_item_creator():
    """Items created by the inactive user are reassigned to the active user."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item = factories.ItemFactory(creator=inactive)

    create_reconciliation(active, inactive).process_reconciliation_request()

    item.refresh_from_db()
    assert item.creator == active


def test_models_user_reconciliation_reassigns_invitation_issuer():
    """Invitations issued by the inactive user are reassigned to the active user."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    invitation = factories.InvitationFactory(issuer=inactive)

    create_reconciliation(active, inactive).process_reconciliation_request()

    invitation.refresh_from_db()
    assert invitation.issuer == active


def test_models_user_reconciliation_toggles_is_active_and_sends_done_email():
    """Processing activates the active user, deactivates the inactive one, and notifies."""
    active = factories.UserFactory(email="active@example.com", is_active=False)
    inactive = factories.UserFactory(email="inactive@example.com", is_active=True)

    reconciliation = create_reconciliation(active, inactive)
    reconciliation.process_reconciliation_request()

    active.refresh_from_db()
    inactive.refresh_from_db()
    assert active.is_active is True
    assert inactive.is_active is False
    assert reconciliation.status == "done"

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 1
    # pylint: disable-next=no-member
    assert mail.outbox[0].to == ["active@example.com"]


def _encrypted_item_with_keys(**accesses):
    """
    Create an encrypted item and one access per given user, mapping each user to
    a (role, wrapped key, key version) tuple.
    """
    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, is_encrypted=True)
    created = {}
    for name, (user, role, key, version) in accesses.items():
        created[name] = factories.UserItemAccessFactory(
            item=item,
            user=user,
            role=role,
            encrypted_item_symmetric_key_for_user=key,
            encryption_public_key_version=version,
        )
    return item, created


def test_models_user_reconciliation_encrypted_transferred_access_becomes_pending():
    """
    A wrapped key belongs to the identity of the inactive user: when another member
    still holds a key on the item, the transferred access becomes pending.
    """
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    _item, accesses = _encrypted_item_with_keys(
        inactive=(inactive, models.RoleChoices.EDITOR, "inactive_key", 2),
        other=(factories.UserFactory(), models.RoleChoices.OWNER, "other_key", 1),
    )

    create_reconciliation(active, inactive).process_reconciliation_request()

    access = accesses["inactive"]
    access.refresh_from_db()
    assert access.user == active
    assert access.role == models.RoleChoices.EDITOR
    assert access.encrypted_item_symmetric_key_for_user is None
    assert access.encryption_public_key_version is None

    other = accesses["other"]
    other.refresh_from_db()
    assert other.encrypted_item_symmetric_key_for_user == "other_key"


def test_models_user_reconciliation_encrypted_last_wrapped_key_is_kept():
    """
    The last wrapped key on an item is kept on the transferred access: dropping it
    would leave the content with nobody able to re-share its key.
    """
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    _item, accesses = _encrypted_item_with_keys(
        inactive=(inactive, models.RoleChoices.OWNER, "inactive_key", 2),
        pending=(factories.UserFactory(), models.RoleChoices.READER, None, None),
    )

    create_reconciliation(active, inactive).process_reconciliation_request()

    access = accesses["inactive"]
    access.refresh_from_db()
    assert access.user == active
    assert access.encrypted_item_symmetric_key_for_user == "inactive_key"
    assert access.encryption_public_key_version == 2


def test_models_user_reconciliation_encrypted_last_wrapped_key_copied_on_conflict():
    """
    When the active user already has a pending access on the item, the last wrapped
    key is copied onto it before the access of the inactive user is removed.
    """
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item, accesses = _encrypted_item_with_keys(
        active=(active, models.RoleChoices.READER, None, None),
        inactive=(inactive, models.RoleChoices.READER, "inactive_key", 2),
    )

    create_reconciliation(active, inactive).process_reconciliation_request()

    assert not models.ItemAccess.objects.filter(pk=accesses["inactive"].pk).exists()
    active_access = models.ItemAccess.objects.get(item=item, user=active)
    assert active_access.role == models.RoleChoices.READER
    assert active_access.encrypted_item_symmetric_key_for_user == "inactive_key"
    assert active_access.encryption_public_key_version == 2


def test_models_user_reconciliation_encrypted_conflict_keeps_active_access_pending():
    """
    When another member holds a key, the key of the inactive user is dropped with its
    access and the access of the active user keeps its own state, merging the role.
    """
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item, accesses = _encrypted_item_with_keys(
        active=(active, models.RoleChoices.READER, None, None),
        inactive=(inactive, models.RoleChoices.EDITOR, "inactive_key", 2),
        other=(factories.UserFactory(), models.RoleChoices.OWNER, "other_key", 1),
    )

    create_reconciliation(active, inactive).process_reconciliation_request()

    assert not models.ItemAccess.objects.filter(pk=accesses["inactive"].pk).exists()
    active_access = models.ItemAccess.objects.get(item=item, user=active)
    assert active_access.role == models.RoleChoices.EDITOR
    assert active_access.encrypted_item_symmetric_key_for_user is None
    assert active_access.encryption_public_key_version is None


def test_models_user_reconciliation_plain_access_conflict_same_role_untouched():
    """On a plaintext item, an access of the active user with the same role is left as is."""
    active = factories.UserFactory(email="active@example.com")
    inactive = factories.UserFactory(email="inactive@example.com")
    item = factories.ItemFactory()
    active_access = factories.UserItemAccessFactory(
        item=item, user=active, role=models.RoleChoices.EDITOR
    )
    inactive_access = factories.UserItemAccessFactory(
        item=item, user=inactive, role=models.RoleChoices.EDITOR
    )
    reconciliation = create_reconciliation(active, inactive)

    updated, removed = reconciliation.prepare_itemaccess_reconciliation()

    assert updated == []
    assert removed == [inactive_access]
    active_access.refresh_from_db()
    assert active_access.role == models.RoleChoices.EDITOR
