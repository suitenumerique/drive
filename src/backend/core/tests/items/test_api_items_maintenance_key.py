"""Tests for the maintenance escrow copy carried by encryption roots."""

import base64
import logging
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def _copy(tag=b"wrap"):
    """A maintenance escrow copy shaped as the vault writes it: version, key id, wrap."""
    return base64.b64encode(bytes([1]) + bytes(range(16)) + tag).decode()


def _client(user):
    client = APIClient()
    client.force_login(user)
    return client


def _encrypted_root(user, role="owner", maintenance_key=None, **kwargs):
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        is_encrypted=True,
        encrypted_symmetric_key=None,
        maintenance_wrapped_item_key=maintenance_key,
        **kwargs,
    )
    factories.UserItemAccessFactory(item=item, user=user, role=role)
    factories.ItemEncryptionKeyWrapFactory(item=item, user=user, wrapped_key="WRAP-USER-ROOT")
    return item


def _encrypted_child(parent, *, item_type=models.ItemTypeChoices.FOLDER):
    return factories.ItemFactory(
        type=item_type,
        parent=parent,
        is_encrypted=True,
        encrypted_symmetric_key=f"CHAIN-WRAP-{uuid4().hex[:8]}",
    )


# ============================================================================
# encrypt / remove-encryption
# ============================================================================


def _encrypt_payload(user, **extra):
    return {
        "encrypted_symmetric_key_per_user": {user.sub: "encrypted_key_for_user"},
        "encryption_public_key_version_per_user": {user.sub: 1},
        "encrypted_keys_for_descendants": {},
        **extra,
    }


def test_api_items_encrypt_stores_the_maintenance_copy_on_the_root():
    """The copy returned by the vault for the new root key is stored on the root."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        _encrypt_payload(user, maintenance_key=_copy()),
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["has_maintenance_key"] is True
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key == _copy()


def test_api_items_encrypt_by_someone_else_than_the_creator_leaves_the_copy_to_backfill():
    """
    The vault escrows for the caller's organization: an administrator's copy could
    be another organization's than the creator's. Left empty, the key chain then
    asks the next holder to backfill it for the creator.
    """
    creator = factories.UserFactory()
    admin = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        creator=creator,
        users=[(creator, models.RoleChoices.OWNER), (admin, models.RoleChoices.ADMIN)],
    )
    payload = {
        "encrypted_symmetric_key_per_user": {
            creator.sub: "encrypted_key_for_creator",
            admin.sub: "encrypted_key_for_admin",
        },
        "encryption_public_key_version_per_user": {creator.sub: 1, admin.sub: 1},
        "encrypted_keys_for_descendants": {},
        "maintenance_key": _copy(b"admin organization"),
    }

    response = _client(admin).patch(f"/api/v1.0/items/{item.id!s}/encrypt/", payload, format="json")

    assert response.status_code == 200, response.json()
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key is None

    key_chain = _client(admin).get(f"/api/v1.0/items/{item.id!s}/key-chain/").json()

    assert key_chain["maintenance_escrow"] == {
        "root_item_id": str(item.pk),
        "owner_sub": creator.sub,
        "has_maintenance_key": False,
        "can_store": True,
    }


def test_api_items_encrypt_without_maintenance_copy():
    """No escrow configured, or the owner not covered: the root has no copy."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/", _encrypt_payload(user), format="json"
    )

    assert response.status_code == 200
    assert response.json()["has_maintenance_key"] is False
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key is None


def test_api_items_encrypt_refuses_a_malformed_maintenance_copy():
    """A value that is not a maintenance copy is refused and nothing is encrypted."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        _encrypt_payload(user, maintenance_key="not base64!"),
        format="json",
    )

    assert response.status_code == 400
    assert [error["attr"] for error in response.json()["errors"]] == ["maintenance_key"]
    item.refresh_from_db()
    assert item.is_encrypted is False


def test_api_items_remove_encryption_clears_the_maintenance_copy():
    """Plaintext again: the copy has nothing left to open."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
        is_encrypted=True,
        maintenance_wrapped_item_key=_copy(),
    )

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/remove-encryption/",
        {"file_key_mapping": {str(item.pk): "new_plaintext.txt"}},
        format="json",
    )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key is None


# ============================================================================
# maintenance-key endpoint
# ============================================================================


def test_api_items_maintenance_key_anonymous():
    """Anonymous users cannot store a copy."""
    item = _encrypted_root(factories.UserFactory())

    response = APIClient().patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": _copy()},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "role, status",
    [("reader", 403), ("editor", 204), ("administrator", 204), ("owner", 204)],
)
def test_api_items_maintenance_key_needs_the_update_ability(role, status):
    """Only users who can update the root store its copy: a reader could store garbage."""
    user = factories.UserFactory()
    item = _encrypted_root(user, role=role)

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": _copy(b"backfilled")},
        format="json",
    )

    assert response.status_code == status
    item.refresh_from_db()
    expected = _copy(b"backfilled") if status == 204 else None
    assert item.maintenance_wrapped_item_key == expected


def _replacement(key_id):
    return base64.b64encode(bytes([1]) + key_id + b"new").decode()


@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_items_maintenance_key_replaced_by_an_owner_or_administrator(role, caplog):
    """Replacing a copy is theirs, and leaves a trace naming both keys."""
    user = factories.UserFactory()
    item = _encrypted_root(user, role=role, maintenance_key=_copy(b"old"))
    new_key_id = bytes(range(32, 48))

    with caplog.at_level(logging.WARNING, logger="core.api.viewsets"):
        response = _client(user).patch(
            f"/api/v1.0/items/{item.id!s}/maintenance-key/",
            {"maintenance_key": _replacement(new_key_id)},
            format="json",
        )

    assert response.status_code == 204
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key == _replacement(new_key_id)
    assert (
        f"Maintenance escrow copy of item {item.pk} replaced by user {user.pk}: "
        f"key {new_key_id.hex()}, was {bytes(range(16)).hex()}"
    ) in caplog.messages


def test_api_items_maintenance_key_not_replaced_by_an_editor():
    """An editor fills an empty copy, never replaces a good one."""
    user = factories.UserFactory()
    item = _encrypted_root(user, role="editor", maintenance_key=_copy(b"old"))

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": _replacement(bytes(range(32, 48)))},
        format="json",
    )

    assert response.status_code == 403
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key == _copy(b"old")


def test_api_items_maintenance_key_stored_when_the_root_has_none():
    """A backfill fills the empty copy, and the item is not taken as edited."""
    user = factories.UserFactory()
    item = _encrypted_root(user)
    updated_at = item.updated_at

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": _copy(b"backfilled")},
        format="json",
    )

    assert response.status_code == 204
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key == _copy(b"backfilled")
    assert item.updated_at == updated_at


@pytest.mark.parametrize("role", ["editor", "owner"])
def test_api_items_maintenance_key_refused_for_the_key_already_stored(role):
    """
    A copy for the same maintenance key brings nothing, even with another wrap (a
    share returns one with fresh randomness): refused, the stored copy kept.
    """
    user = factories.UserFactory()
    item = _encrypted_root(user, role=role, maintenance_key=_copy(b"stored"))

    for value in (_copy(b"stored"), _copy(b"other randomness")):
        response = _client(user).patch(
            f"/api/v1.0/items/{item.id!s}/maintenance-key/",
            {"maintenance_key": value},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["code"] == "maintenance_key_already_stored"
        item.refresh_from_db()
        assert item.maintenance_wrapped_item_key == _copy(b"stored")


def test_api_items_maintenance_key_replaced_for_another_key_leaves_updated_at():
    """A copy for a new maintenance key replaces the old one without editing the item."""
    user = factories.UserFactory()
    item = _encrypted_root(user, maintenance_key=_copy(b"old"))
    updated_at = item.updated_at

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": _replacement(bytes(range(32, 48)))},
        format="json",
    )

    assert response.status_code == 204
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key == _replacement(bytes(range(32, 48)))
    assert item.updated_at == updated_at


def test_api_items_maintenance_key_refused_on_a_nested_item():
    """Nested items chain from the root's key: only the root carries a copy."""
    user = factories.UserFactory()
    root = _encrypted_root(user)
    child = _encrypted_child(root)

    response = _client(user).patch(
        f"/api/v1.0/items/{child.id!s}/maintenance-key/",
        {"maintenance_key": _copy()},
        format="json",
    )

    assert response.status_code == 400
    child.refresh_from_db()
    assert child.maintenance_wrapped_item_key is None


def test_api_items_maintenance_key_refused_on_a_plaintext_item():
    """A plaintext item has no key to escrow."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": _copy()},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not base64!",
        base64.b64encode(bytes([2]) + bytes(range(16)) + b"wrap").decode(),
        base64.b64encode(bytes([1]) + bytes(range(16))).decode(),
    ],
)
def test_api_items_maintenance_key_refuses_a_malformed_copy(value):
    """Not base64, an unknown version, or no wrap after the header: refused."""
    user = factories.UserFactory()
    item = _encrypted_root(user)

    response = _client(user).patch(
        f"/api/v1.0/items/{item.id!s}/maintenance-key/",
        {"maintenance_key": value},
        format="json",
    )

    assert response.status_code == 400
    item.refresh_from_db()
    assert item.maintenance_wrapped_item_key is None


# ============================================================================
# serializer and key-chain
# ============================================================================


def test_api_items_has_maintenance_key_only_on_roots():
    """Roots say whether they carry a copy, other items say nothing; the copy never leaves."""
    user = factories.UserFactory()
    root = _encrypted_root(user, maintenance_key=_copy())
    child = _encrypted_child(root)
    client = _client(user)

    root_data = client.get(f"/api/v1.0/items/{root.id!s}/").json()
    child_data = client.get(f"/api/v1.0/items/{child.id!s}/").json()

    assert root_data["has_maintenance_key"] is True
    assert child_data["has_maintenance_key"] is None
    assert _copy() not in str(root_data)


def test_api_items_key_chain_describes_the_root_escrow_when_entering_at_the_root():
    """The entry key is the root's: the caller can refresh its copy, for its owner."""
    owner = factories.UserFactory()
    editor = factories.UserFactory()
    root = _encrypted_root(owner, creator=owner)
    factories.UserItemAccessFactory(item=root, user=editor, role="editor")
    factories.ItemEncryptionKeyWrapFactory(item=root, user=editor, wrapped_key="WRAP-EDITOR-ROOT")
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)

    data = _client(editor).get(f"/api/v1.0/items/{file_item.id!s}/key-chain/").json()

    assert data["maintenance_escrow"] == {
        "root_item_id": str(root.pk),
        "owner_sub": owner.sub,
        "has_maintenance_key": False,
        "can_store": True,
    }
    assert data["item_creator_sub"] == file_item.creator.sub


def test_api_items_key_chain_has_no_escrow_for_a_side_door_entry():
    """An outsider entering through a demoted item's own wrap holds no root key."""
    owner = factories.UserFactory()
    outsider = factories.UserFactory()
    root = _encrypted_root(owner)
    hybrid = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=hybrid, user=outsider, role="reader")
    factories.ItemEncryptionKeyWrapFactory(
        item=hybrid, user=outsider, wrapped_key="WRAP-OUTSIDER-HYBRID"
    )

    data = _client(outsider).get(f"/api/v1.0/items/{hybrid.id!s}/key-chain/").json()

    assert data["user_access_item_id"] == str(hybrid.pk)
    assert data["maintenance_escrow"] is None


# ============================================================================
# move
# ============================================================================


def test_api_items_move_re_anchor_stores_the_new_root_copy():
    """Moved out of its tree, the item becomes a root with its own copy."""
    user = factories.UserFactory()
    root = _encrypted_root(user)
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)
    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")]
    )

    response = _client(user).post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(plain_target.id),
            "is_encryption_root": True,
            "per_user_encrypted_keys": {user.sub: "WRAP-USER-NEW-ROOT"},
            "encryption_public_key_versions": {user.sub: 1},
            "maintenance_key": _copy(b"new-root"),
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    file_item.refresh_from_db()
    assert file_item.encrypted_symmetric_key is None
    assert file_item.maintenance_wrapped_item_key == _copy(b"new-root")


def test_api_items_move_refuses_a_copy_outside_a_re_anchor():
    """A chained item never carries a copy, whatever the move."""
    user = factories.UserFactory()
    root = _encrypted_root(user)
    folder_a = _encrypted_child(root)
    folder_b = _encrypted_child(root)
    file_item = _encrypted_child(folder_a, item_type=models.ItemTypeChoices.FILE)

    response = _client(user).post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(folder_b.id),
            "encrypted_symmetric_key": "CHAIN-WRAP-B",
            "maintenance_key": _copy(),
        },
        format="json",
    )

    assert response.status_code == 400
    assert [error["attr"] for error in response.json()["errors"]] == ["maintenance_key"]


def test_api_items_move_demote_clears_the_copy():
    """Attached under another root, the item is covered by that root's copy."""
    user = factories.UserFactory()
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        is_encrypted=True,
        encrypted_symmetric_key=None,
        maintenance_wrapped_item_key=_copy(),
    )
    factories.UserItemAccessFactory(item=file_item, user=user, role="owner")
    factories.ItemEncryptionKeyWrapFactory(
        item=file_item, user=user, wrapped_key="WRAP-USER-FILE-ROOT"
    )
    dest_root = _encrypted_root(user)

    response = _client(user).post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "is_encryption_root": False,
            "encrypted_symmetric_key": "CHAIN-WRAP-UNDER-DEST",
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    file_item.refresh_from_db()
    assert file_item.maintenance_wrapped_item_key is None
