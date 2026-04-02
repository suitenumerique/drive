"""Tests for encryption of items on API endpoint."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

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
        {"encryptedSymmetricKeyPerUser": {}, "encryptedKeysForDescendants": {}},
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
        {"encryptedSymmetricKeyPerUser": {}, "encryptedKeysForDescendants": {}},
        format="json",
    )
    assert response.status_code == 403 or response.status_code == 404


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
        {"encryptedSymmetricKeyPerUser": {user.sub: "fake_key"}},
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
            "encryptedSymmetricKeyPerUser": {user.sub: "encrypted_key_for_user"},
            "encryptedKeysForDescendants": {},
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
            "encryptedSymmetricKeyPerUser": {user.sub: "root_key_for_user"},
            "encryptedKeysForDescendants": {
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
        {"encryptedSymmetricKeyPerUser": {user.sub: "key"}},
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
        {"encryptedSymmetricKeyPerUser": {user.sub: "key"}},
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
        {"encryptedSymmetricKeyPerUser": {user1.sub: "key1"}},
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
        {},
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


# ============================================================================
# Constraints: invitations blocked for encrypted items
# ============================================================================


def test_api_items_invitation_blocked_for_encrypted():
    """Cannot create invitation on encrypted item."""
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
    assert response.status_code == 400
    assert "not supported" in str(response.json()).lower()


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
