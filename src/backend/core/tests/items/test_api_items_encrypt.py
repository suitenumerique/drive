"""Tests for encryption of items on API endpoint."""

from unittest import mock

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers

pytestmark = pytest.mark.django_db


# ============================================================================
# encrypt endpoint
# ============================================================================


def test_api_items_encrypt_anonymous():
    """Anonymous users should not be able to encrypt an item."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    response = APIClient().patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {"encrypted_symmetric_key_per_user": {}, "encrypted_keys_for_descendants": {}},
        format="json",
    )
    assert response.status_code == 401


def test_api_items_encrypt_authenticated_unrelated():
    """Users without access cannot encrypt an item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {"encrypted_symmetric_key_per_user": {}, "encrypted_keys_for_descendants": {}},
        format="json",
    )
    assert response.status_code in {403, 404}


def test_api_items_encrypt_reader_forbidden():
    """Readers should not be able to encrypt an item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.READER)],
    )

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {"encrypted_symmetric_key_per_user": {user.sub: "fake_key"}},
        format="json",
    )
    assert response.status_code == 403


def test_api_items_encrypt_standalone_file():
    """Owner should be able to encrypt a standalone file."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {
            "encrypted_symmetric_key_per_user": {user.sub: "encrypted_key_for_user"},
            "encryption_public_key_version_per_user": {user.sub: 1},
            "encrypted_keys_for_descendants": {},
        },
        format="json",
    )
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.is_encrypted is True
    assert item.encrypted_symmetric_key is None  # root, no parent-wrapped key

    # Check the access has the per-user key
    access = models.ItemAccess.objects.get(item=item, user=user)
    assert access.encrypted_item_symmetric_key_for_user == "encrypted_key_for_user"


def test_api_items_encrypt_folder_with_children():
    """Owner should be able to encrypt a folder and all its descendants."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    subfolder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        parent=folder,
    )
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=subfolder,
    )

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{folder.id!s}/encrypt/",
        {
            "encrypted_symmetric_key_per_user": {user.sub: "root_key_for_user"},
            "encryption_public_key_version_per_user": {user.sub: 1},
            "encrypted_keys_for_descendants": {
                str(subfolder.pk): "subfolder_wrapped_key",
                str(file_item.pk): "file_wrapped_key",
            },
        },
        format="json",
    )
    assert response.status_code == 200

    folder.refresh_from_db()
    subfolder.refresh_from_db()
    file_item.refresh_from_db()

    assert folder.is_encrypted is True
    assert folder.encrypted_symmetric_key is None  # root
    assert subfolder.is_encrypted is True
    assert subfolder.encrypted_symmetric_key == "subfolder_wrapped_key"
    assert file_item.is_encrypted is True
    assert file_item.encrypted_symmetric_key == "file_wrapped_key"


def test_api_items_encrypt_not_restricted():
    """Cannot encrypt an item that is not restricted."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.PUBLIC,
        users=[(user, models.RoleChoices.OWNER)],
    )

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {"encrypted_symmetric_key_per_user": {user.sub: "key"}},
        format="json",
    )
    assert response.status_code == 400
    assert "restricted" in response.json()["detail"].lower()


def test_api_items_encrypt_already_encrypted():
    """Cannot encrypt an already-encrypted item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {"encrypted_symmetric_key_per_user": {user.sub: "key"}},
        format="json",
    )
    assert response.status_code == 400
    assert "already encrypted" in response.json()["detail"].lower()


def test_api_items_encrypt_missing_user_keys():
    """Must provide keys for all users with access."""
    user1 = factories.UserFactory()
    user2 = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[
            (user1, models.RoleChoices.OWNER),
            (user2, models.RoleChoices.READER),
        ],
    )

    client = APIClient()
    client.force_login(user1)
    # Only provide key for user1, missing user2
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {
            "encrypted_symmetric_key_per_user": {user1.sub: "key1"},
            "encryption_public_key_version_per_user": {user1.sub: 1},
        },
        format="json",
    )
    assert response.status_code == 400
    assert "missing_users" in response.json() or "do not match" in response.json()["detail"].lower()


# ============================================================================
# remove-encryption endpoint
# ============================================================================


def test_api_items_remove_encryption():
    """Owner should be able to remove encryption from an encrypted item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    access = models.ItemAccess.objects.get(item=item, user=user)
    access.encrypted_item_symmetric_key_for_user = "some_key"
    access.save()

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/remove-encryption/",
        # File root needs an entry in `file_key_mapping` for itself
        # (the new S3 key the frontend uploaded the plaintext to).
        {"file_key_mapping": {str(item.pk): "new_plaintext.txt"}},
        format="json",
    )
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.is_encrypted is False
    assert item.encrypted_symmetric_key is None

    access.refresh_from_db()
    assert access.encrypted_item_symmetric_key_for_user is None


def test_api_items_remove_encryption_not_root():
    """Cannot remove encryption from an item that's not an encryption root."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.encrypted_symmetric_key = "wrapped_by_parent"  # not a root
    item.save()

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/remove-encryption/",
        {},
        format="json",
    )
    assert response.status_code == 400
    assert "encryption root" in response.json()["detail"].lower()


# ============================================================================
# key-chain endpoint
# ============================================================================


def test_api_items_key_chain():
    """User should get key chain from their access point to the target item."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    subfolder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        parent=folder,
    )
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=subfolder,
    )

    # Set up encryption state
    folder.is_encrypted = True
    folder.save()
    subfolder.is_encrypted = True
    subfolder.encrypted_symmetric_key = "subfolder_wrapped"
    subfolder.save()
    file_item.is_encrypted = True
    file_item.encrypted_symmetric_key = "file_wrapped"
    file_item.save()

    # Set up per-user key on the folder access
    access = models.ItemAccess.objects.get(item=folder, user=user)
    access.encrypted_item_symmetric_key_for_user = "root_key_for_user"
    access.save()

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{file_item.id!s}/key-chain/")
    assert response.status_code == 200

    data = response.json()
    assert data["user_access_item_id"] == str(folder.pk)
    assert data["encrypted_key_for_user"] == "root_key_for_user"
    assert len(data["chain"]) == 2  # subfolder + file
    assert data["chain"][0]["item_id"] == str(subfolder.pk)
    assert data["chain"][0]["encrypted_symmetric_key"] == "subfolder_wrapped"
    assert data["chain"][1]["item_id"] == str(file_item.pk)
    assert data["chain"][1]["encrypted_symmetric_key"] == "file_wrapped"


def test_api_items_key_chain_direct_access():
    """When user has direct access to the item, chain should be empty."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    access = models.ItemAccess.objects.get(item=item, user=user)
    access.encrypted_item_symmetric_key_for_user = "direct_key"
    access.save()

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/key-chain/")
    assert response.status_code == 200

    data = response.json()
    assert data["encrypted_key_for_user"] == "direct_key"
    assert data["chain"] == []


def test_api_items_key_chain_prefers_root_over_hybrid_wrap():
    """
    Chain user with a hybrid wrap (chain item that ALSO carries a
    per-user wrap on its access row, e.g. a self-rooted file demoted
    into the chain) must enter the tree at the encryption root, not
    via the side-door wrap on the chain item itself. Otherwise chain
    operations like move-rewrap end up with chain=[] and crash on the
    frontend (`chain[-1]` undefined).
    """
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    folder.is_encrypted = True  # encryption root (no chain wrap)
    folder.save()
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
    )
    file_item.is_encrypted = True
    file_item.encrypted_symmetric_key = "file_chain_wrapped"  # chain wrap
    file_item.save()

    # User's wrap on the encryption root.
    root_access = models.ItemAccess.objects.get(item=folder, user=user)
    root_access.encrypted_item_symmetric_key_for_user = "root_key_for_user"
    root_access.save()

    # User ALSO has a per-user wrap on the file itself — the hybrid
    # state produced by the demote flow (a self-rooted file moved
    # INTO this chain keeps its per-user wrap so outsiders aren't
    # revoked). The walker must prefer the root wrap over this one.
    factories.UserItemAccessFactory(
        item=file_item,
        user=user,
        role="owner",
        encrypted_item_symmetric_key_for_user="hybrid_side_door_wrap",
        encryption_public_key_version=1,
    )

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{file_item.id!s}/key-chain/")
    assert response.status_code == 200

    data = response.json()
    # Entry resolves at the root, not the file (despite the file's
    # access row having a non-null wrap).
    assert data["user_access_item_id"] == str(folder.pk)
    assert data["encrypted_key_for_user"] == "root_key_for_user"
    # And the chain is non-empty so the frontend can rewrap.
    assert len(data["chain"]) == 1
    assert data["chain"][0]["item_id"] == str(file_item.pk)
    assert data["chain"][0]["encrypted_symmetric_key"] == "file_chain_wrapped"


def test_api_items_key_chain_falls_back_to_hybrid_for_outsiders():
    """
    Outsider user with NO access to the encryption root, only a
    per-user wrap on a chain item (preserved by the demote flow), can
    still resolve a key chain via the side-door wrap. The two-pass
    walker falls back from "root entries only" to "any non-null wrap"
    when no root entry is found.
    """
    owner = factories.UserFactory()
    outsider = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(owner, models.RoleChoices.OWNER)],
    )
    folder.is_encrypted = True
    folder.save()
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
    )
    file_item.is_encrypted = True
    file_item.encrypted_symmetric_key = "file_chain_wrapped"
    file_item.save()

    # Outsider has access to the FILE only (per-user wrap from when
    # it was self-rooted; preserved through the demote into `folder`).
    factories.UserItemAccessFactory(
        item=file_item,
        user=outsider,
        role="reader",
        encrypted_item_symmetric_key_for_user="outsider_wrap",
        encryption_public_key_version=4,
    )

    client = APIClient()
    client.force_login(outsider)
    response = client.get(f"/api/v1.0/items/{file_item.id!s}/key-chain/")
    assert response.status_code == 200

    data = response.json()
    # No root entry available → fallback resolves at the file itself.
    assert data["user_access_item_id"] == str(file_item.pk)
    assert data["encrypted_key_for_user"] == "outsider_wrap"
    assert data["chain"] == []


# ============================================================================
# Invitations: an invitee has no account, hence no encryption key, so their
# invitation becomes a pending access (no wrapped key) when they sign up.
# ============================================================================


def test_api_items_invitation_allowed_for_encrypted():
    """Invitations can be created on an encrypted item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        {"email": "new@example.com", "role": "reader"},
        format="json",
    )
    assert response.status_code == 201


def test_api_items_encrypt_with_pending_invitation():
    """A pending invitation does not block encrypting, and the invitee signs
    up as a pending member."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    factories.InvitationFactory(item=item, issuer=user, email="new@example.com")

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/encrypt/",
        {
            "encrypted_symmetric_key_per_user": {user.sub: "encrypted_key_for_user"},
            "encryption_public_key_version_per_user": {user.sub: 1},
            "encrypted_keys_for_descendants": {},
        },
        format="json",
    )
    assert response.status_code == 200

    newcomer = factories.UserFactory(email="new@example.com")
    access = models.ItemAccess.objects.get(item=item, user=newcomer)
    assert access.encrypted_item_symmetric_key_for_user is None


# ============================================================================
# Constraints: link configuration blocked for encrypted items
# ============================================================================


def test_api_items_link_config_blocked_for_encrypted():
    """Cannot change encrypted item away from RESTRICTED."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    client = APIClient()
    client.force_login(user)
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        {"link_reach": "public", "link_role": "reader"},
        format="json",
    )
    assert response.status_code == 400
    assert "encrypted" in response.json()["detail"].lower()


# ============================================================================
# Constraints: team access blocked for encrypted items
# ============================================================================


def test_api_items_team_access_blocked_for_encrypted():
    """Cannot create team access on encrypted item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        {
            "team": "some_team",
            "role": "reader",
            "encrypted_item_symmetric_key_for_user": "key",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "team" in str(response.json()).lower()


# ============================================================================
# Children in encrypted folder
# ============================================================================


def test_api_items_children_create_in_encrypted_folder():
    """Creating a child in an encrypted folder requires encrypted_symmetric_key."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    folder.is_encrypted = True
    folder.save()

    client = APIClient()
    client.force_login(user)

    # Without encrypted_symmetric_key → should fail
    response = client.post(
        f"/api/v1.0/items/{folder.id!s}/children/",
        {"title": "subfolder", "type": "folder"},
        format="json",
    )
    assert response.status_code == 400
    assert "encrypted_symmetric_key" in str(response.json()).lower()

    # With encrypted_symmetric_key → should succeed
    response = client.post(
        f"/api/v1.0/items/{folder.id!s}/children/",
        {
            "title": "subfolder",
            "type": "folder",
            "encrypted_symmetric_key": "wrapped_key",
        },
        format="json",
    )
    assert response.status_code == 201

    child = models.Item.objects.get(title="subfolder")
    assert child.is_encrypted is True
    assert child.encrypted_symmetric_key == "wrapped_key"


# ============================================================================
# WOPI disabled for encrypted items
# ============================================================================


def test_api_items_wopi_disabled_for_encrypted():
    """WOPI ability should be False for encrypted items."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.RESTRICTED,
        users=[(user, models.RoleChoices.OWNER)],
    )
    item.is_encrypted = True
    item.save()

    abilities = item.get_abilities(user)
    assert abilities["wopi"] is False


# ============================================================================
# Operations refused on encrypted items
# ============================================================================


def _encrypt(item, key_holder=None, key="wrapped_key", version=1):
    """Mark an item encrypted and give the key holder a wrapped key on it."""
    item.is_encrypted = True
    item.save()
    if key_holder is not None:
        models.ItemAccess.objects.filter(item=item, user=key_holder).update(
            encrypted_item_symmetric_key_for_user=key,
            encryption_public_key_version=version,
        )


def test_api_items_duplicate_refused_for_encrypted():
    """An encrypted file cannot be duplicated: the copy would hold unreadable ciphertext."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, models.RoleChoices.OWNER)],
    )
    assert item.get_abilities(user)["duplicate"] is True
    _encrypt(item, user)

    client = APIClient()
    client.force_login(user)
    with mock.patch("core.tasks.item.duplicate_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403
    mock_delay.assert_not_called()
    assert models.Item.objects.count() == 1


def test_api_items_convert_refused_for_encrypted(settings):
    """An encrypted file cannot be sent to the conversion service."""
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = "test-jwt-secret"
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="document.doc",
        mimetype="application/msword",
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, models.RoleChoices.OWNER)],
    )
    assert item.get_abilities(user)["convert"] is True
    _encrypt(item, user)

    client = APIClient()
    client.force_login(user)
    with mock.patch("core.api.viewsets.convert_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/convert/")

    assert response.status_code == 403
    mock_delay.assert_not_called()
    assert not models.Item.objects.filter(
        upload_state=models.ItemUploadStateChoices.CONVERTING
    ).exists()


def test_api_items_export_refused_for_encrypted_folder():
    """An encrypted folder cannot be exported as an archive."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )
    assert folder.get_abilities(user)["export"] is True
    _encrypt(folder, user)

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{folder.id!s}/export/")

    assert response.status_code == 403


def test_api_items_restrict_refused_for_encrypted_folder():
    """An encrypted folder cannot be restricted: it would leave its key chain."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )
    assert folder.get_abilities(user)["restrict"] is True
    _encrypt(folder, user)

    client = APIClient()
    client.force_login(user)
    response = client.post(f"/api/v1.0/items/{folder.id!s}/restrict/")

    assert response.status_code == 403
    folder.refresh_from_db()
    assert folder.is_restricted is False
    assert str(folder.path) == f"{parent.id!s}.{folder.id!s}"

    with pytest.raises(ValidationError) as excinfo:
        folder.restrict(user)
    assert excinfo.value.error_dict["is_restricted"][0].code == "item_restrict_encrypted"


def test_api_items_unrestrict_refused_for_encrypted_folder():
    """A restricted folder that became encrypted cannot be unrestricted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    _encrypt(folder, user)

    client = APIClient()
    client.force_login(user)
    response = client.delete(f"/api/v1.0/items/{folder.id!s}/restrict/")

    assert response.status_code == 403
    folder.refresh_from_db()
    assert folder.is_restricted is True


def test_models_items_unrestrict_refused_into_encrypted_parent():
    """A plaintext restricted folder cannot be reattached inside an encrypted folder."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    _encrypt(parent, user)

    with pytest.raises(ValidationError) as excinfo:
        folder.unrestrict()
    assert excinfo.value.error_dict["is_restricted"][0].code == "item_unrestrict_encrypted"

    folder.refresh_from_db()
    assert folder.is_restricted is True
    assert str(folder.path) == str(folder.id)


def test_api_items_children_from_template_refused_in_encrypted_folder():
    """A template would be written in plaintext: refused inside an encrypted folder."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )
    _encrypt(folder, user)

    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{folder.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
            "encrypted_symmetric_key": "wrapped_key",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "template" in str(response.json()).lower()
    assert models.Item.objects.filter(title="my document").exists() is False


# ============================================================================
# Encryption fields in list payloads
# ============================================================================


def _encrypted_folder_with_children(owner, pending_user, nb_children):
    """Build an encrypted root folder shared with a pending member, with encrypted files."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(owner, models.RoleChoices.OWNER), (pending_user, models.RoleChoices.READER)],
    )
    _encrypt(folder, owner, version=3)
    children = [
        factories.ItemFactory(
            parent=folder,
            type=models.ItemTypeChoices.FILE,
            update_upload_state=models.ItemUploadStateChoices.READY,
            is_encrypted=True,
            encrypted_symmetric_key=f"child_wrapped_{index}",
        )
        for index in range(nb_children)
    ]
    return folder, children


def test_api_items_children_list_encryption_fields():
    """Children of an encrypted folder expose the encryption state of the viewer."""
    owner = factories.UserFactory()
    pending_user = factories.UserFactory()
    folder, _children = _encrypted_folder_with_children(owner, pending_user, 2)

    client = APIClient()
    client.force_login(owner)
    response = client.get(f"/api/v1.0/items/{folder.id!s}/children/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    for result in results:
        assert result["is_encrypted"] is True
        assert result["is_encryption_root"] is False
        assert result["is_inside_encrypted_subtree"] is True
        assert result["is_pending_encryption_for_user"] is False
        assert result["encryption_public_key_version_for_user"] == 3
        assert result["accesses_user_ids"] == sorted([owner.sub, pending_user.sub])

    client.force_login(pending_user)
    response = client.get(f"/api/v1.0/items/{folder.id!s}/children/")

    assert response.status_code == 200
    for result in response.json()["results"]:
        assert result["is_pending_encryption_for_user"] is True
        assert result["encryption_public_key_version_for_user"] is None

    response = client.get(f"/api/v1.0/items/{folder.id!s}/")

    assert response.status_code == 200
    assert response.json()["is_encryption_root"] is True
    assert response.json()["is_inside_encrypted_subtree"] is False
    assert response.json()["is_pending_encryption_for_user"] is True
    assert response.json()["encrypted_item_symmetric_key_for_user"] is None


def test_api_items_children_list_encryption_fields_match_unannotated_serializer():
    """The annotated list values are the ones the serializer computes on its own."""
    owner = factories.UserFactory()
    pending_user = factories.UserFactory()
    folder, children = _encrypted_folder_with_children(owner, pending_user, 1)
    fields = [
        "accesses_user_ids",
        "encryption_public_key_version_for_user",
        "is_encryption_root",
        "is_inside_encrypted_subtree",
        "is_pending_encryption_for_user",
    ]

    for user in (owner, pending_user):
        client = APIClient()
        client.force_login(user)
        listed = client.get(f"/api/v1.0/items/{folder.id!s}/children/").json()["results"][0]

        request = RequestFactory().get("/")
        request.user = user
        child = models.Item.objects.get(pk=children[0].pk)
        serialized = serializers.ListItemSerializer(child, context={"request": request}).data

        assert {field: listed[field] for field in fields} == {
            field: serialized[field] for field in fields
        }


def test_api_items_children_list_encryption_fields_constant_queries():
    """The encryption fields cost no query per listed item."""
    owner = factories.UserFactory()
    pending_user = factories.UserFactory()
    small_folder, _children = _encrypted_folder_with_children(owner, pending_user, 1)
    large_folder, _children = _encrypted_folder_with_children(owner, pending_user, 4)

    client = APIClient()
    client.force_login(pending_user)
    query_counts = []
    for folder in (small_folder, large_folder):
        # Warm the nb_accesses cache so that both requests run the same queries
        client.get(f"/api/v1.0/items/{folder.id!s}/children/")
        with CaptureQueriesContext(connection) as queries:
            response = client.get(f"/api/v1.0/items/{folder.id!s}/children/")
        assert response.status_code == 200
        query_counts.append(len(queries))

    assert query_counts[0] == query_counts[1]
