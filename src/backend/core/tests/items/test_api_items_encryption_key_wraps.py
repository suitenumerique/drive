"""Tests for the per-user wraps of encrypted items' keys, kept apart from the accesses."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def _client(user):
    client = APIClient()
    client.force_login(user)
    return client


def _shared_folder_with_encrypted_root(owner, *members):
    """A plaintext folder shared with `members`, holding an encryption root only
    `owner` holds the key of."""
    shared = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(owner, models.RoleChoices.OWNER), *members],
    )
    root = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        parent=shared,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.ItemEncryptionKeyWrapFactory(item=root, user=owner, wrapped_key="OWNER-WRAP")
    return shared, root


# ============================================================================
# encrypt endpoint
# ============================================================================


def test_api_items_encrypt_inherited_users_get_wraps_without_accesses():
    """
    Encrypting a subfolder gives its key to the users inheriting a role on it, and to
    them only: no access row is created, so their roles keep coming from the ancestor.
    A pending user (null wrap) gets nothing stored.
    """
    owner = factories.UserFactory()
    member = factories.UserFactory()
    pending = factories.UserFactory()
    shared = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[
            (owner, models.RoleChoices.OWNER),
            (member, models.RoleChoices.EDITOR),
            (pending, models.RoleChoices.READER),
        ],
    )
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, parent=shared)
    child = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, parent=folder)

    response = _client(owner).patch(
        f"/api/v1.0/items/{folder.id!s}/encrypt/",
        {
            "encrypted_symmetric_key_per_user": {
                owner.sub: "OWNER-WRAP",
                member.sub: "MEMBER-WRAP",
                pending.sub: None,
            },
            "encryption_public_key_version_per_user": {
                owner.sub: 1,
                member.sub: 2,
                pending.sub: None,
            },
            "encrypted_keys_for_descendants": {str(child.pk): "CHILD-CHAIN-WRAP"},
        },
        format="json",
    )

    assert response.status_code == 200
    assert not models.ItemAccess.objects.filter(item__in=[folder, child]).exists()
    wraps = {
        wrap.user_id: (wrap.wrapped_key, wrap.encryption_public_key_version)
        for wrap in models.ItemEncryptionKeyWrap.objects.all()
    }
    assert wraps == {owner.id: ("OWNER-WRAP", 1), member.id: ("MEMBER-WRAP", 2)}

    accesses = _client(owner).get(f"/api/v1.0/items/{folder.id!s}/accesses/").json()
    assert {entry["user"]["id"]: entry["is_pending_encryption"] for entry in accesses} == {
        str(owner.id): False,
        str(member.id): False,
        str(pending.id): True,
    }


def test_api_items_encrypt_pending_user_sees_item_pending():
    """A user inheriting a role on an encrypted item without a wrap of its key sees it pending."""
    owner = factories.UserFactory()
    newcomer = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner, (newcomer, models.RoleChoices.READER))

    newcomer_view = _client(newcomer).get(f"/api/v1.0/items/{root.id!s}/").json()
    assert newcomer_view["is_pending_encryption_for_user"] is True
    assert newcomer_view["encrypted_item_symmetric_key_for_user"] is None

    owner_view = _client(owner).get(f"/api/v1.0/items/{root.id!s}/").json()
    assert owner_view["is_pending_encryption_for_user"] is False
    assert owner_view["encrypted_item_symmetric_key_for_user"] == "OWNER-WRAP"


def test_api_items_encrypt_drops_leftover_wraps():
    """A wrap left from a former encryption goes: kept, it would hide a pending user."""
    owner = factories.UserFactory()
    pending = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(owner, models.RoleChoices.OWNER), (pending, models.RoleChoices.READER)],
    )
    factories.ItemEncryptionKeyWrapFactory(item=folder, user=pending, wrapped_key="OLD-WRAP")

    response = _client(owner).patch(
        f"/api/v1.0/items/{folder.id!s}/encrypt/",
        {
            "encrypted_symmetric_key_per_user": {owner.sub: "OWNER-WRAP", pending.sub: None},
            "encryption_public_key_version_per_user": {owner.sub: 1, pending.sub: None},
            "encrypted_keys_for_descendants": {},
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    assert not models.ItemEncryptionKeyWrap.objects.filter(user=pending).exists()


# ============================================================================
# accept endpoint
# ============================================================================


def test_api_items_encryption_key_wraps_accept_pending_user():
    """A key holder gives the key to a user pending through an ancestor's access."""
    owner = factories.UserFactory()
    pending = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner, (pending, models.RoleChoices.READER))

    response = _client(owner).put(
        f"/api/v1.0/items/{root.id!s}/encryption-key-wraps/",
        {
            "user_id": str(pending.id),
            "encrypted_item_symmetric_key_for_user": "PENDING-WRAP",
            "encryption_public_key_version": 3,
        },
        format="json",
    )

    assert response.status_code == 204
    wrap = models.ItemEncryptionKeyWrap.objects.get(item=root, user=pending)
    assert wrap.wrapped_key == "PENDING-WRAP"
    assert wrap.encryption_public_key_version == 3
    assert not models.ItemAccess.objects.filter(item=root).exists()


def test_api_items_encryption_key_wraps_accept_below_root_with_root_wrap():
    """
    A pending user whose access is on an item inside an encrypted folder gets that
    item's key, stored on it, from a key holder entering the chain at the root.
    """
    owner = factories.UserFactory()
    pending = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner)
    child = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=root,
        is_encrypted=True,
        encrypted_symmetric_key="CHILD-CHAIN-WRAP",
    )
    factories.UserItemAccessFactory(item=child, user=pending, role="reader")

    response = _client(owner).put(
        f"/api/v1.0/items/{child.id!s}/encryption-key-wraps/",
        {
            "user_id": str(pending.id),
            "encrypted_item_symmetric_key_for_user": "CHILD-WRAP",
            "encryption_public_key_version": 1,
        },
        format="json",
    )

    assert response.status_code == 204
    wrap = models.ItemEncryptionKeyWrap.objects.get(user=pending)
    assert (wrap.item_id, wrap.wrapped_key) == (child.id, "CHILD-WRAP")


def test_api_items_encryption_key_wraps_accept_requires_caller_wrap():
    """A manager without a wrap of the item's key has nothing to have wrapped."""
    owner = factories.UserFactory()
    admin = factories.UserFactory()
    pending = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(
        owner,
        (admin, models.RoleChoices.ADMIN),
        (pending, models.RoleChoices.READER),
    )

    response = _client(admin).put(
        f"/api/v1.0/items/{root.id!s}/encryption-key-wraps/",
        {
            "user_id": str(pending.id),
            "encrypted_item_symmetric_key_for_user": "PENDING-WRAP",
            "encryption_public_key_version": 1,
        },
        format="json",
    )

    assert response.status_code == 403
    assert not models.ItemEncryptionKeyWrap.objects.filter(user=pending).exists()


def test_api_items_encryption_key_wraps_accept_requires_manage_role():
    """Only members managing the accesses accept pending users."""
    owner = factories.UserFactory()
    editor = factories.UserFactory()
    pending = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(
        owner,
        (editor, models.RoleChoices.EDITOR),
        (pending, models.RoleChoices.READER),
    )
    factories.ItemEncryptionKeyWrapFactory(item=root, user=editor)

    response = _client(editor).put(
        f"/api/v1.0/items/{root.id!s}/encryption-key-wraps/",
        {
            "user_id": str(pending.id),
            "encrypted_item_symmetric_key_for_user": "PENDING-WRAP",
            "encryption_public_key_version": 1,
        },
        format="json",
    )

    assert response.status_code == 403
    assert not models.ItemEncryptionKeyWrap.objects.filter(user=pending).exists()


def test_api_items_encryption_key_wraps_accept_refuses_user_without_access():
    """The key is never given to someone without a role on the item."""
    owner = factories.UserFactory()
    stranger = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner)

    response = _client(owner).put(
        f"/api/v1.0/items/{root.id!s}/encryption-key-wraps/",
        {
            "user_id": str(stranger.id),
            "encrypted_item_symmetric_key_for_user": "STRANGER-WRAP",
            "encryption_public_key_version": 1,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "user_without_access"
    assert not models.ItemEncryptionKeyWrap.objects.filter(user=stranger).exists()


def test_api_items_encryption_key_wraps_accept_refuses_user_not_pending():
    """A user already holding a wrap on the key chain is not pending."""
    owner = factories.UserFactory()
    member = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner, (member, models.RoleChoices.READER))
    factories.ItemEncryptionKeyWrapFactory(item=root, user=member, wrapped_key="MEMBER-WRAP")

    response = _client(owner).put(
        f"/api/v1.0/items/{root.id!s}/encryption-key-wraps/",
        {
            "user_id": str(member.id),
            "encrypted_item_symmetric_key_for_user": "OTHER-WRAP",
            "encryption_public_key_version": 1,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "access_not_pending"
    assert models.ItemEncryptionKeyWrap.objects.get(item=root, user=member).wrapped_key == (
        "MEMBER-WRAP"
    )


# ============================================================================
# revocation
# ============================================================================


def test_api_item_accesses_delete_removes_wraps_below():
    """Removing a user's access on an ancestor removes the keys it let them hold."""
    owner = factories.UserFactory()
    member = factories.UserFactory()
    shared, root = _shared_folder_with_encrypted_root(owner, (member, models.RoleChoices.EDITOR))
    factories.ItemEncryptionKeyWrapFactory(item=root, user=member)
    access = models.ItemAccess.objects.get(item=shared, user=member)

    response = _client(owner).delete(f"/api/v1.0/items/{shared.id!s}/accesses/{access.id!s}/")

    assert response.status_code == 204
    assert not models.ItemEncryptionKeyWrap.objects.filter(user=member).exists()
    assert models.ItemEncryptionKeyWrap.objects.filter(user=owner).exists()


def test_api_item_accesses_delete_keeps_wraps_still_reachable():
    """A user keeping a role through another access keeps their key."""
    owner = factories.UserFactory()
    member = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner, (member, models.RoleChoices.EDITOR))
    direct = factories.UserItemAccessFactory(item=root, user=member, role="administrator")
    factories.ItemEncryptionKeyWrapFactory(item=root, user=member)

    response = _client(owner).delete(f"/api/v1.0/items/{root.id!s}/accesses/{direct.id!s}/")

    assert response.status_code == 204
    assert models.ItemEncryptionKeyWrap.objects.filter(item=root, user=member).exists()


def test_api_item_accesses_delete_refused_when_it_strands_pending_users():
    """
    Removing the last user holding the key while pending users remain would leave the
    folder undecryptable by anyone: refused, and nothing is removed.
    """
    owner = factories.UserFactory()
    holder = factories.UserFactory()
    pending = factories.UserFactory()
    shared = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[
            (owner, models.RoleChoices.OWNER),
            (holder, models.RoleChoices.EDITOR),
            (pending, models.RoleChoices.READER),
        ],
    )
    root = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        parent=shared,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.ItemEncryptionKeyWrapFactory(item=root, user=holder)
    access = models.ItemAccess.objects.get(item=shared, user=holder)

    response = _client(owner).delete(f"/api/v1.0/items/{shared.id!s}/accesses/{access.id!s}/")

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "would_strand_pending_users"
    assert models.ItemAccess.objects.filter(pk=access.pk).exists()
    assert models.ItemEncryptionKeyWrap.objects.filter(item=root, user=holder).exists()


def test_api_items_move_out_of_shared_folder_removes_wraps_of_former_members():
    """Moving an encryption root out of a shared folder takes the key from its members."""
    owner = factories.UserFactory()
    member = factories.UserFactory()
    _shared, root = _shared_folder_with_encrypted_root(owner, (member, models.RoleChoices.EDITOR))
    factories.ItemEncryptionKeyWrapFactory(item=root, user=member)
    private = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(owner, models.RoleChoices.OWNER)],
    )

    response = _client(owner).post(
        f"/api/v1.0/items/{root.id!s}/move/",
        {"target_item_id": str(private.id)},
        format="json",
    )

    assert response.status_code == 200, response.json()
    assert not models.ItemEncryptionKeyWrap.objects.filter(user=member).exists()
    assert models.ItemEncryptionKeyWrap.objects.filter(item=root, user=owner).exists()


# ============================================================================
# key chain
# ============================================================================


def test_api_items_key_chain_gives_the_version_of_the_wrap_it_returns():
    """
    With two wraps on the chain, /key-chain/ enters at the root and gives that wrap's
    version, while the item list reports the user's latest wrap.
    """
    owner = factories.UserFactory()
    root = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(owner, models.RoleChoices.OWNER)],
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.ItemEncryptionKeyWrapFactory(
        item=root, user=owner, wrapped_key="ROOT-WRAP", encryption_public_key_version=1
    )
    file = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=root,
        is_encrypted=True,
        encrypted_symmetric_key="FILE-CHAIN-WRAP",
    )
    factories.ItemEncryptionKeyWrapFactory(
        item=file, user=owner, wrapped_key="FILE-WRAP", encryption_public_key_version=2
    )

    key_chain = _client(owner).get(f"/api/v1.0/items/{file.id!s}/key-chain/").json()

    assert key_chain["user_access_item_id"] == str(root.id)
    assert key_chain["encrypted_key_for_user"] == "ROOT-WRAP"
    assert key_chain["encryption_public_key_version"] == 1
