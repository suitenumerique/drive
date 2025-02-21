"""
Unit tests for the item model
"""

import random
import smtplib
from logging import Logger
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_items_str():
    """The str representation should be the title of the item."""
    item = factories.ItemFactory(title="admins")
    assert str(item) == "admins"


def test_models_items_id_unique():
    """The "id" field should be unique."""
    item = factories.ItemFactory()
    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(id=item.id)

    assert exc_info.value.message_dict == {"id": ["Item with this Id already exists."]}


def test_models_items_title_max_length():
    """The "title" field should be 100 characters maximum."""
    factories.ItemFactory(title="a" * 255)
    with pytest.raises(
        ValidationError,
        match=r"Ensure this value has at most 255 characters \(it has 256\)\.",
    ):
        factories.ItemFactory(title="a" * 256)


def test_models_items_file_key():
    """The file key should be built from the instance uuid."""
    item = factories.ItemFactory(
        id="9531a5f1-42b1-496c-b3f4-1c09ed139b3c",
        type=models.ItemTypeChoices.FILE,
        filename="logo.png",
    )
    assert item.file_key == "item/9531a5f1-42b1-496c-b3f4-1c09ed139b3c/logo.png"


@pytest.mark.parametrize("depth", range(5))
def test_models_items_soft_delete(depth):
    """Trying to delete an item that is already deleted or is a descendant of
    a deleted item should raise an error.
    """
    items = []
    for i in range(depth + 1):
        items.append(
            factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
            if i == 0
            else factories.ItemFactory(
                parent=items[-1], type=models.ItemTypeChoices.FOLDER
            )
        )
    assert models.Item.objects.count() == depth + 1

    # Delete any one of the items...
    deleted_item = random.choice(items)
    deleted_item.soft_delete()

    with pytest.raises(RuntimeError) as exc_info:
        items[-1].soft_delete()
        assert str(exc_info) == "This item is already deleted or has deleted ancestors."

    assert deleted_item.deleted_at is not None
    assert deleted_item.ancestors_deleted_at == deleted_item.deleted_at

    descendants = deleted_item.descendants()
    for child in descendants:
        assert child.id != deleted_item.id
        assert child.deleted_at is None
        assert child.ancestors_deleted_at is not None
        assert child.ancestors_deleted_at == deleted_item.deleted_at

    ancestors = deleted_item.ancestors()
    for parent in ancestors:
        assert parent.id != deleted_item.id
        assert parent.deleted_at is None
        assert parent.ancestors_deleted_at is None

    assert len(ancestors) + len(descendants) == depth


# get_abilities


@pytest.mark.parametrize(
    "is_authenticated,reach,role",
    [
        (True, "restricted", "reader"),
        (True, "restricted", "editor"),
        (False, "restricted", "reader"),
        (False, "restricted", "editor"),
        (False, "authenticated", "reader"),
        (False, "authenticated", "editor"),
    ],
)
def test_models_items_get_abilities_forbidden(
    is_authenticated, reach, role, django_assert_num_queries
):
    """
    Check abilities returned for an item giving insufficient roles to link holders
    i.e anonymous users or authenticated users who have no specific role on the item.
    """
    item = factories.ItemFactory(link_reach=reach, link_role=role)
    user = factories.UserFactory() if is_authenticated else AnonymousUser()
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": False,
        "children_create": False,
        "children_list": False,
        "destroy": False,
        "favorite": False,
        "invite_owner": False,
        "media_auth": False,
        "move": False,
        "link_configuration": False,
        "partial_update": False,
        "restore": False,
        "retrieve": False,
        "update": False,
        "upload_ended": False,
    }
    nb_queries = 1 if is_authenticated else 0
    with django_assert_num_queries(nb_queries):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert item.get_abilities(user) == expected_abilities


@pytest.mark.parametrize(
    "is_authenticated,reach",
    [
        (True, "public"),
        (False, "public"),
        (True, "authenticated"),
    ],
)
def test_models_items_get_abilities_reader(
    is_authenticated, reach, django_assert_num_queries
):
    """
    Check abilities returned for a item giving reader role to link holders
    i.e anonymous users or authenticated users who have no specific role on the item.
    """
    item = factories.ItemFactory(link_reach=reach, link_role="reader")
    user = factories.UserFactory() if is_authenticated else AnonymousUser()
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": False,
        "children_create": False,
        "children_list": True,
        "destroy": False,
        "favorite": is_authenticated,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": False,
        "restore": False,
        "retrieve": True,
        "update": False,
        "upload_ended": False,
    }
    nb_queries = 1 if is_authenticated else 0
    with django_assert_num_queries(nb_queries):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


@pytest.mark.parametrize(
    "is_authenticated,reach",
    [
        (True, "public"),
        (False, "public"),
        (True, "authenticated"),
    ],
)
def test_models_items_get_abilities_editor(
    is_authenticated, reach, django_assert_num_queries
):
    """
    Check abilities returned for a item giving editor role to link holders
    i.e anonymous users or authenticated users who have no specific role on the item.
    """
    item = factories.ItemFactory(link_reach=reach, link_role="editor")
    user = factories.UserFactory() if is_authenticated else AnonymousUser()
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": False,
        "children_create": is_authenticated,
        "children_list": True,
        "destroy": False,
        "favorite": is_authenticated,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": True,
        "restore": False,
        "retrieve": True,
        "update": True,
        "upload_ended": False,
    }
    nb_queries = 1 if is_authenticated else 0
    with django_assert_num_queries(nb_queries):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


def test_models_items_get_abilities_owner(django_assert_num_queries):
    """Check abilities returned for the owner of a item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    expected_abilities = {
        "accesses_manage": True,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": True,
        "favorite": True,
        "invite_owner": True,
        "link_configuration": True,
        "media_auth": True,
        "move": True,
        "partial_update": True,
        "restore": True,
        "retrieve": True,
        "update": True,
        "upload_ended": True,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    expected_abilities["move"] = False
    assert item.get_abilities(user) == expected_abilities


def test_models_items_get_abilities_administrator(django_assert_num_queries):
    """Check abilities returned for the administrator of a item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "administrator")])
    expected_abilities = {
        "accesses_manage": True,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": True,
        "media_auth": True,
        "move": True,
        "partial_update": True,
        "restore": False,
        "retrieve": True,
        "update": True,
        "upload_ended": True,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


def test_models_items_get_abilities_editor_user(django_assert_num_queries):
    """Check abilities returned for the editor of a item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "editor")])
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": True,
        "restore": False,
        "retrieve": True,
        "update": True,
        "upload_ended": False,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


def test_models_items_get_abilities_reader_user(django_assert_num_queries):
    """Check abilities returned for the reader of a item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "reader")])
    access_from_link = item.link_reach != "restricted" and item.link_role == "editor"
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": access_from_link,
        "children_list": True,
        "destroy": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": access_from_link,
        "restore": False,
        "retrieve": True,
        "update": access_from_link,
        "upload_ended": False,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


def test_models_items_get_abilities_preset_role(django_assert_num_queries):
    """No query is done if the role is preset e.g. with query annotation."""
    access = factories.UserItemAccessFactory(role="reader", item__link_role="reader")
    access.item.user_roles = ["reader"]

    with django_assert_num_queries(0):
        abilities = access.item.get_abilities(access.user)

    assert abilities == {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": False,
        "children_list": True,
        "destroy": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": False,
        "restore": False,
        "retrieve": True,
        "update": False,
        "upload_ended": False,
    }


def test_models_items__email_invitation__success():
    """
    The email invitation is sent successfully.
    """
    item = factories.ItemFactory()

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0

    sender = factories.UserFactory(full_name="Test Sender", email="sender@example.com")
    item.send_invitation_email(
        "guest@example.com", models.RoleChoices.EDITOR, sender, "en"
    )

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 1

    # pylint: disable-next=no-member
    email = mail.outbox[0]

    assert email.to == ["guest@example.com"]
    email_content = " ".join(email.body.split())

    assert (
        f"Test Sender (sender@example.com) invited you with the role &quot;editor&quot; "
        f"on the following item: {item.title}" in email_content
    )
    assert f"items/{item.id}/" in email_content


def test_models_items__email_invitation__success_fr():
    """
    The email invitation is sent successfully in french.
    """
    item = factories.ItemFactory()

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0

    sender = factories.UserFactory(
        full_name="Test Sender2", email="sender2@example.com"
    )
    item.send_invitation_email(
        "guest2@example.com",
        models.RoleChoices.OWNER,
        sender,
        "fr-fr",
    )

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 1

    # pylint: disable-next=no-member
    email = mail.outbox[0]

    assert email.to == ["guest2@example.com"]
    email_content = " ".join(email.body.split())

    assert (
        f"Test Sender2 (sender2@example.com) vous a invité avec le rôle &quot;propriétaire&quot; "
        f"sur le item suivant: {item.title}" in email_content
    )
    assert f"items/{item.id}/" in email_content


@mock.patch(
    "core.models.send_mail",
    side_effect=smtplib.SMTPException("Error SMTPException"),
)
@mock.patch.object(Logger, "error")
def test_models_items__email_invitation__failed(mock_logger, _mock_send_mail):
    """Check mail behavior when an SMTP error occurs when sent an email invitation."""
    item = factories.ItemFactory()

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0

    sender = factories.UserFactory()
    item.send_invitation_email(
        "guest3@example.com",
        models.RoleChoices.ADMIN,
        sender,
        "en",
    )

    # No email has been sent
    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0

    # Logger should be called
    mock_logger.assert_called_once()

    (
        _,
        emails,
        exception,
    ) = mock_logger.call_args.args

    assert emails == ["guest3@example.com"]
    assert isinstance(exception, smtplib.SMTPException)


# item number of accesses


def test_models_items_nb_accesses_cache_is_set_and_retrieved(
    django_assert_num_queries,
):
    """Test that nb_accesses is cached after the first computation."""
    item = factories.ItemFactory()
    key = f"item_{item.id!s}_nb_accesses"
    nb_accesses = random.randint(1, 4)
    factories.UserItemAccessFactory.create_batch(nb_accesses, item=item)
    factories.UserItemAccessFactory()  # An unrelated access should not be counted

    # Initially, the nb_accesses should not be cached
    assert cache.get(key) is None

    # Compute the nb_accesses for the first time (this should set the cache)
    with django_assert_num_queries(1):
        assert item.nb_accesses == nb_accesses

    # Ensure that the nb_accesses is now cached
    with django_assert_num_queries(0):
        assert item.nb_accesses == nb_accesses
    assert cache.get(key) == nb_accesses

    # The cache value should be invalidated when a item access is created
    models.ItemAccess.objects.create(
        item=item, user=factories.UserFactory(), role="reader"
    )
    assert cache.get(key) is None  # Cache should be invalidated
    with django_assert_num_queries(1):
        new_nb_accesses = item.nb_accesses
    assert new_nb_accesses == nb_accesses + 1
    assert cache.get(key) == new_nb_accesses  # Cache should now contain the new value


def test_models_items_nb_accesses_cache_is_invalidated_on_access_removal(
    django_assert_num_queries,
):
    """Test that the cache is invalidated when a item access is deleted."""
    item = factories.ItemFactory()
    key = f"item_{item.id!s}_nb_accesses"
    access = factories.UserItemAccessFactory(item=item)

    # Initially, the nb_accesses should be cached
    assert item.nb_accesses == 1
    assert cache.get(key) == 1

    # Remove the access and check if cache is invalidated
    access.delete()
    assert cache.get(key) is None  # Cache should be invalidated

    # Recompute the nb_accesses (this should trigger a cache set)
    with django_assert_num_queries(1):
        new_nb_accesses = item.nb_accesses
    assert new_nb_accesses == 0
    assert cache.get(key) == 0  # Cache should now contain the new value


@pytest.mark.parametrize("item_type", models.ItemTypeChoices.values)
def test_models_items_default_upload_state(item_type):
    """The default value for the upload_state field depends on the item type."""
    item = factories.ItemFactory(type=item_type)
    assert item.upload_state == (
        models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None
    )


def test_models_items_creating_file_without_filename_should_fail():
    """Creating a file item without a filename should raise an error."""
    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename=None)

    assert exc_info.value.message_dict == {
        "__all__": ["Constraint “check_filename_set_for_files” is violated."]
    }


@pytest.mark.parametrize(
    "item_type",
    [
        t[0]
        for t in models.ItemTypeChoices.choices
        if t[0] != models.ItemTypeChoices.FILE
    ],
)
def test_models_items_creating_non_file_with_filename_should_fail(item_type):
    """Creating a non-file item with a filename should raise an error."""
    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(type=item_type, filename="file.txt")

    assert exc_info.value.message_dict == {
        "__all__": ["Constraint “check_filename_set_for_files” is violated."]
    }


def test_models_items_title_must_be_set():
    """The title field must be set."""
    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(title=None)

    assert exc_info.value.message_dict == {"title": ["This field cannot be null."]}

    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(title="")

    assert exc_info.value.message_dict == {"title": ["This field cannot be blank."]}


def test_models_items_unique_title_in_current_path():
    """Check title unicity in the current path."""
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, title="folder")
    parent2 = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, title="an other one"
    )

    # An other root can have the same title
    factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, title="folder")

    # Create a child item with the same title should work
    factories.ItemFactory(
        parent=parent, title="folder", type=models.ItemTypeChoices.FOLDER
    )
    # Create a child item with a title already existing in an other tree should work
    factories.ItemFactory(
        parent=parent, title="an other one", type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(
        parent=parent2, title="folder", type=models.ItemTypeChoices.FOLDER
    )

    factories.ItemFactory(
        parent=parent,
        title="file.txt",
        type=models.ItemTypeChoices.FILE,
        filename="file.txt",
    )

    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(
            parent=parent, title="folder", type=models.ItemTypeChoices.FOLDER
        )
        assert exc_info.value.message_dict == {
            "title": "title already exists in this folder."
        }

    with pytest.raises(ValidationError) as exc_info:
        factories.ItemFactory(
            parent=parent,
            title="file.txt",
            type=models.ItemTypeChoices.FILE,
            filename="file.txt",
        )
        assert exc_info.value.message_dict == {
            "title": "title already exists in this folder."
        }


def test_models_items_numchild():
    """The numchild property should return the number of children."""
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    assert parent.numchild == 0

    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    parent.refresh_from_db()
    assert parent.numchild == 1

    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    parent.refresh_from_db()
    assert parent.numchild == 2

    to_delete = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    parent.refresh_from_db()
    assert parent.numchild == 3

    to_delete.soft_delete()
    parent.refresh_from_db()
    assert parent.numchild == 2

    to_delete.restore()
    parent.refresh_from_db()
    assert parent.numchild == 3


def test_models_items_numchild_folder():
    """The numchild_folder property should return the number of folder children."""
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    assert parent.numchild_folder == 0

    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    parent.refresh_from_db()
    assert parent.numchild_folder == 1

    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    parent.refresh_from_db()
    assert parent.numchild_folder == 1

    to_delete = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    parent.refresh_from_db()
    assert parent.numchild_folder == 2

    to_delete.soft_delete()
    parent.refresh_from_db()
    assert parent.numchild_folder == 1

    to_delete.restore()
    parent.refresh_from_db()
    assert parent.numchild_folder == 2


def test_models_items_restore():
    """The restore method should restore a soft-deleted item."""
    item = factories.ItemFactory()
    item.soft_delete()
    item.refresh_from_db()
    assert item.deleted_at is not None
    assert item.ancestors_deleted_at == item.deleted_at

    item.restore()
    item.refresh_from_db()
    assert item.deleted_at is None
    assert item.ancestors_deleted_at == item.deleted_at


def test_models_items_restore_complex():
    """The restore method should restore a soft-deleted item and its ancestors."""
    grand_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    child1 = factories.ItemFactory(parent=item)
    child2 = factories.ItemFactory(parent=item)

    # Soft delete first the item
    item.soft_delete()
    item.refresh_from_db()
    child1.refresh_from_db()
    child2.refresh_from_db()
    assert item.deleted_at is not None
    assert item.ancestors_deleted_at == item.deleted_at
    assert child1.ancestors_deleted_at == item.deleted_at
    assert child2.ancestors_deleted_at == item.deleted_at

    # Soft delete the grand parent
    grand_parent.soft_delete()
    grand_parent.refresh_from_db()
    parent.refresh_from_db()
    assert grand_parent.deleted_at is not None
    assert grand_parent.ancestors_deleted_at == grand_parent.deleted_at
    assert parent.ancestors_deleted_at == grand_parent.deleted_at
    # item, child1 and child2 should not be affected
    item.refresh_from_db()
    child1.refresh_from_db()
    child2.refresh_from_db()
    assert item.deleted_at is not None
    assert item.ancestors_deleted_at == item.deleted_at
    assert child1.ancestors_deleted_at == item.deleted_at
    assert child2.ancestors_deleted_at == item.deleted_at

    # Restore the item
    item.restore()
    item.refresh_from_db()
    child1.refresh_from_db()
    child2.refresh_from_db()
    grand_parent.refresh_from_db()
    assert item.deleted_at is None
    assert item.ancestors_deleted_at == grand_parent.deleted_at
    # child 1 and child 2 should now have the same ancestors_deleted_at as the grand parent
    assert child1.ancestors_deleted_at == grand_parent.deleted_at
    assert child2.ancestors_deleted_at == grand_parent.deleted_at


def test_models_items_restore_complex_bis():
    """The restore method should restore a soft-deleted item and its ancestors."""
    grand_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    child1 = factories.ItemFactory(parent=item)
    child2 = factories.ItemFactory(parent=item)

    # Soft delete first the item
    item.soft_delete()
    item.refresh_from_db()
    child1.refresh_from_db()
    child2.refresh_from_db()
    assert item.deleted_at is not None
    assert item.ancestors_deleted_at == item.deleted_at
    assert child1.ancestors_deleted_at == item.deleted_at
    assert child2.ancestors_deleted_at == item.deleted_at

    # Soft delete the grand parent
    grand_parent.soft_delete()
    grand_parent.refresh_from_db()
    parent.refresh_from_db()
    assert grand_parent.deleted_at is not None
    assert grand_parent.ancestors_deleted_at == grand_parent.deleted_at
    assert parent.ancestors_deleted_at == grand_parent.deleted_at
    # item, child1 and child2 should not be affected
    item.refresh_from_db()
    child1.refresh_from_db()
    child2.refresh_from_db()
    assert item.deleted_at is not None
    assert item.ancestors_deleted_at == item.deleted_at
    assert child1.ancestors_deleted_at == item.deleted_at
    assert child2.ancestors_deleted_at == item.deleted_at

    # Restoring the grand parent should all the tree
    grand_parent.restore()
    grand_parent.refresh_from_db()
    parent.refresh_from_db()
    item.refresh_from_db()
    child1.refresh_from_db()
    child2.refresh_from_db()
    assert grand_parent.deleted_at is None
    assert grand_parent.ancestors_deleted_at is None
    assert parent.deleted_at is None
    assert parent.ancestors_deleted_at is None
    assert item.deleted_at is not None
    assert item.ancestors_deleted_at == item.deleted_at
    assert child1.ancestors_deleted_at == item.deleted_at
    assert child2.ancestors_deleted_at == item.deleted_at
