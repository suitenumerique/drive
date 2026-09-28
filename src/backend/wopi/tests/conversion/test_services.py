"""Tests for the conversion service."""

from unittest import mock

from django.core.files.base import ContentFile
from django.db import DatabaseError

import pytest

from core import factories, models
from wopi.conversion import exceptions, services
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend

pytestmark = pytest.mark.django_db


class FakeBackend:
    """Conversion backend returning fixed converted content."""

    def convert(self, _item, _source_url, target_extension):
        """Return fake converted content."""
        return ContentFile(b"converted", name=f"converted.{target_extension}")


@pytest.fixture(autouse=True)
def _fake_backend(request):
    """Use a fake backend except in tests that exercise backend resolution."""
    if request.node.name.startswith("test_resolve_backend"):
        yield
        return

    with mock.patch.object(services, "resolve_backend", return_value=FakeBackend()):
        yield


def _configure_wopi(settings, client="onlyoffice", options=None):
    """Wire a WOPI client config covering .doc files."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example"
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = "test-jwt-secret"
    settings.WOPI_CLIENTS_CONFIGURATION = {
        client: {
            "options": options
            or {
                "ForceConvertExtensions": ["doc"],
                "ConvertServiceUrl": "http://onlyoffice/converter",
            },
        }
    }


def _file(user, **kwargs):
    """Build a ready .doc file the user can update; kwargs override defaults."""
    defaults = {
        "users": [(user, models.RoleChoices.EDITOR)],
        "type": models.ItemTypeChoices.FILE,
        "filename": "document.doc",
        "mimetype": "application/msword",
        "update_upload_state": models.ItemUploadStateChoices.READY,
    }
    defaults.update(kwargs)
    return factories.ItemFactory(**defaults)


def test_convert_item_creates_converted_file_copy(settings):
    """Create a modern-format copy for a forced legacy file conversion."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FOLDER,
    )
    item = _file(
        user,
        parent=parent,
    )

    converted = services.convert_item(item, user)

    assert converted.filename == "document (converted).docx"
    assert converted.parent().id == parent.id
    assert converted.upload_state == models.ItemUploadStateChoices.READY


def test_convert_item_keeps_original_file_unchanged(settings):
    """Leave the source file unchanged after conversion."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, size=123)
    original_parent = item.parent()

    services.convert_item(item, user)

    item.refresh_from_db()
    assert item.filename == "document.doc"
    assert item.parent() == original_parent
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size == 123


def test_convert_item_does_not_copy_explicit_source_accesses(settings):
    """Skip copying explicit source accesses to the converted file."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    other_user = factories.UserFactory()
    item = _file(user)
    factories.UserItemAccessFactory(
        item=item,
        user=other_user,
        role=models.RoleChoices.READER,
    )

    converted = services.convert_item(item, user)

    assert not converted.accesses.filter(user=other_user).exists()


def test_convert_item_keeps_title_and_filename_aligned_on_collision(settings):
    """Keep the converted title and filename aligned when the target name exists."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
        title="document (converted).docx",
        filename="document (converted).docx",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    item = _file(user, parent=parent)

    converted = services.convert_item(item, user)

    assert converted.title == "document (converted)_01.docx"
    assert converted.filename == "document (converted)_01.docx"


def test_convert_item_uses_source_parent_when_user_can_update_it_via_link(settings):
    """Keep the converted file in the parent when a writable link is present."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    item = _file(user, parent=parent)

    converted = services.convert_item(item, user)

    assert converted.parent().id == parent.id


def test_convert_item_falls_back_to_root_when_parent_is_not_writable(settings):
    """Fall back to the user's root when the parent is read-only."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = _file(user, parent=parent)

    converted = services.convert_item(item, user)

    assert converted.parent() is None


def test_convert_item_rejects_non_file_items(settings):
    """Reject non-file items."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FOLDER,
    )

    with pytest.raises(exceptions.ConversionRejected, match="not a file"):
        services.convert_item(item, user)


def test_convert_item_rejects_items_that_are_not_ready(settings):
    """Reject files that are not yet ready."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, update_upload_state=models.ItemUploadStateChoices.PENDING)

    with pytest.raises(exceptions.ConversionRejected, match="not ready"):
        services.convert_item(item, user)


def test_convert_item_rejects_users_without_update_permission(settings):
    """Reject users without update permission on the source file."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="document.doc",
        mimetype="application/msword",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    with pytest.raises(exceptions.ConversionPermissionDenied, match="cannot update"):
        services.convert_item(item, user)


def test_convert_item_rejects_unsupported_extensions(settings):
    """Reject extensions outside the configured legacy set."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, filename="document.docx")

    with pytest.raises(exceptions.ConversionRejected, match="No target conversion"):
        services.convert_item(item, user)


def test_convert_item_rejects_non_onlyoffice_clients(settings):
    """Reject WOPI clients other than OnlyOffice."""
    _configure_wopi(settings, client="collabora")
    user = factories.UserFactory()
    item = _file(user)

    with pytest.raises(exceptions.ConversionRejected, match="No OnlyOffice client"):
        services.convert_item(item, user)


def test_convert_item_rejects_files_without_forced_conversion(settings):
    """Reject files outside the forced-conversion policy."""
    _configure_wopi(settings, options={"ForceConvertExtensions": ["xls"]})
    user = factories.UserFactory()
    item = _file(user)

    with pytest.raises(exceptions.ConversionRejected, match="not forced"):
        services.convert_item(item, user)


def test_convert_item_rejects_missing_onlyoffice_client_config(settings):
    """Reject conversion when WOPI_CLIENTS_CONFIGURATION has no OnlyOffice entry."""
    settings.WOPI_CLIENTS_CONFIGURATION = {}
    user = factories.UserFactory()
    item = _file(user)

    with pytest.raises(exceptions.ConversionRejected, match="No OnlyOffice client"):
        services.convert_item(item, user)


def test_resolve_backend_rejects_missing_convert_service_url():
    """Reject missing ConvertServiceUrl in OnlyOffice options."""
    with pytest.raises(
        exceptions.ConversionMisconfigured, match="Missing OnlyOffice ConvertServiceUrl"
    ):
        services.resolve_backend({})


def test_perform_conversion_removes_saved_file_when_database_save_fails(settings):
    """Delete saved bytes when flipping the placeholder to READY fails."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user)
    placeholder = services.prepare_conversion(item, user)
    saved_keys = []
    deleted_keys = []

    class FakeStorage:
        """Storage fake tracking saved and deleted keys."""

        def save(self, key, _content):
            """Track saved keys."""
            saved_keys.append(key)
            return key

        def delete(self, key):
            """Track deleted keys."""
            deleted_keys.append(key)

    original_save = models.Item.save

    def fail_ready_save(instance, *args, **kwargs):
        """Raise when the placeholder is flipped to READY, pass otherwise."""
        if instance.id == placeholder.id and kwargs.get("update_fields"):
            raise DatabaseError("database write failed")
        return original_save(instance, *args, **kwargs)

    with (
        mock.patch.object(services, "default_storage", FakeStorage()),
        mock.patch.object(models.Item, "save", fail_ready_save),
    ):
        with pytest.raises(DatabaseError, match="database write failed"):
            services.perform_conversion(item, placeholder, user)

    assert deleted_keys == saved_keys


def test_resolve_backend_builds_onlyoffice_backend(settings):
    """Build the OnlyOffice backend from options and settings."""
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = "test-secret"
    backend = services.resolve_backend(
        {"ConvertServiceUrl": "https://office.example/converter"},
    )

    assert isinstance(backend, OnlyOfficeConversionBackend)
    assert backend.convert_service_url == "https://office.example/converter"
    assert backend.jwt_secret == "test-secret"


def test_resolve_backend_raises_when_onlyoffice_url_is_missing():
    """Raise when ConvertServiceUrl is missing from OnlyOffice options."""
    with pytest.raises(
        exceptions.ConversionMisconfigured, match="Missing OnlyOffice ConvertServiceUrl"
    ):
        services.resolve_backend({})


def test_prepare_conversion_raises_when_jwt_secret_is_missing(settings):
    """Reject conversion before creating the placeholder when the secret is missing."""
    _configure_wopi(settings)
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = None
    user = factories.UserFactory()
    item = _file(user)

    with pytest.raises(
        exceptions.ConversionMisconfigured,
        match="Missing WOPI_ONLYOFFICE_CONVERT_JWT_SECRET",
    ):
        services.prepare_conversion(item, user)


def test_prepare_conversion_returns_placeholder_in_converting_state(settings):
    """Create the placeholder in the destination folder with upload_state CONVERTING."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FOLDER,
    )
    item = _file(user, parent=parent)

    placeholder = services.prepare_conversion(item, user)

    assert placeholder.filename == "document (converted).docx"
    assert placeholder.upload_state == models.ItemUploadStateChoices.CONVERTING
    assert placeholder.parent().id == parent.id


def test_prepare_conversion_accepts_analyzing_source(settings):
    """Queue a conversion while the source is still being analyzed."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, update_upload_state=models.ItemUploadStateChoices.ANALYZING)

    placeholder = services.prepare_conversion(item, user)

    assert placeholder.upload_state == models.ItemUploadStateChoices.CONVERTING


def test_perform_conversion_rejects_analyzing_source(settings):
    """Never convert the bytes before analysis confirmed the source is safe."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, update_upload_state=models.ItemUploadStateChoices.ANALYZING)
    placeholder = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FILE,
        filename="document.docx",
        update_upload_state=models.ItemUploadStateChoices.CONVERTING,
    )

    with pytest.raises(exceptions.ConversionRejected, match="not ready"):
        services.perform_conversion(item, placeholder, user)


def test_prepare_conversion_rejects_unsupported_extensions(settings):
    """Skip placeholder creation for files that cannot be converted."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, filename="document.docx")

    with pytest.raises(exceptions.ConversionRejected, match="No target conversion"):
        services.prepare_conversion(item, user)


def test_convert_item_accepts_uppercase_extension(settings):
    """Convert REPORT.DOC the same way as report.doc."""
    _configure_wopi(settings)
    user = factories.UserFactory()
    item = _file(user, filename="REPORT.DOC")

    converted = services.convert_item(item, user)

    assert converted.filename.endswith(".docx")
