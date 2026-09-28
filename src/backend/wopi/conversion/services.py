"""Service layer for server-to-server legacy file conversion."""

from os.path import splitext

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import DatabaseError, transaction
from django.utils.translation import gettext as _

from core import models
from core.api.utils import detect_mimetype
from core.models import Item
from core.utils.item_title import manage_unique_title
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend
from wopi.conversion.exceptions import (
    ConversionMisconfigured,
    ConversionPermissionDenied,
    ConversionRejected,
)
from wopi.conversion.policy import is_forced_conversion, target_extension_for
from wopi.conversion.source_url import build_source_url

MIME_SNIFF_BYTES = 2048


def _validate_conversion(item, user, require_ready=True):
    """Run pre-flight checks and return the target extension and client options."""
    if item.type != models.ItemTypeChoices.FILE:
        raise ConversionRejected("Source item is not a file.")

    ready_states = [models.ItemUploadStateChoices.READY]
    if not require_ready:
        ready_states.append(models.ItemUploadStateChoices.ANALYZING)
    if item.upload_state not in ready_states:
        raise ConversionRejected("Source item is not ready.")

    if not item.get_abilities(user).get("update"):
        raise ConversionPermissionDenied("User cannot update the source item.")

    target_extension = target_extension_for(item.extension)
    if not target_extension:
        raise ConversionRejected("No target conversion for this extension.")

    onlyoffice_config = settings.WOPI_CLIENTS_CONFIGURATION.get("onlyoffice")
    if onlyoffice_config is None:
        raise ConversionRejected("No OnlyOffice client configured.")

    if not settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET:
        raise ConversionMisconfigured("Missing WOPI_ONLYOFFICE_CONVERT_JWT_SECRET")

    client_options = onlyoffice_config.get("options", {})
    if not is_forced_conversion(item, client_options):
        raise ConversionRejected("Conversion not forced by the active WOPI client.")

    return target_extension, client_options


def resolve_backend(client_options):
    """Build the OnlyOffice conversion backend from WOPI client options."""
    convert_service_url = client_options.get("ConvertServiceUrl")
    if not convert_service_url:
        raise ConversionMisconfigured("Missing OnlyOffice ConvertServiceUrl")

    return OnlyOfficeConversionBackend(
        convert_service_url=convert_service_url,
    )


def _resolve_destination_parent(source_item, user):
    """Return the source parent when the user can still update it, else None."""
    if source_item.depth <= 1:
        return None

    parent = source_item.parent()
    if not parent.get_abilities(user).get("children_create"):
        return None

    return parent


def _target_filename(item, target_extension, parent, user):
    """Return a sibling-free filename for the converted item."""
    if parent:
        siblings = Item.objects.children(parent.path)
    else:
        siblings = Item.objects.filter(path__depth=1, accesses__user=user).distinct()

    base, _extension = splitext(item.filename)
    target = f"{base} ({_('converted')}).{target_extension}"

    return manage_unique_title(siblings, target)


def prepare_conversion(source_item, user):
    """Validate inputs and create the placeholder Item receiving the conversion.

    The placeholder is created synchronously and returned to the caller so the
    UI can display the converting state right away. The actual OnlyOffice
    conversion happens later in a celery task.
    """
    target_extension, _ = _validate_conversion(source_item, user, require_ready=False)
    parent = _resolve_destination_parent(source_item, user)
    target_filename = _target_filename(source_item, target_extension, parent, user)

    with transaction.atomic():
        placeholder = Item.objects.create_child(
            creator=user,
            link_reach=None if parent else models.LinkReachChoices.RESTRICTED,
            parent=parent,
            title=target_filename,
            type=models.ItemTypeChoices.FILE,
            filename=target_filename,
            upload_state=models.ItemUploadStateChoices.CONVERTING,
        )
        if placeholder.is_root:
            models.ItemAccess.objects.create(
                item=placeholder,
                user=user,
                role=models.RoleChoices.OWNER,
            )

    return placeholder


def perform_conversion(source_item, placeholder, user):
    """Run the OnlyOffice conversion and attach the result to the placeholder.

    Called from the celery task. The network call to OnlyOffice happens outside
    of any DB transaction; only the final READY update is wrapped in one.
    """
    target_extension, client_options = _validate_conversion(source_item, user)
    source_url = build_source_url(source_item, user)
    converted_file = resolve_backend(client_options).convert(
        source_item, source_url, target_extension
    )

    converted_file.seek(0)
    mimetype = detect_mimetype(
        converted_file.read(min(MIME_SNIFF_BYTES, converted_file.size)),
        filename=placeholder.filename,
    )
    converted_file.seek(0)

    default_storage.save(placeholder.file_key, converted_file)
    try:
        placeholder.mimetype = mimetype
        placeholder.size = converted_file.size
        placeholder.upload_state = models.ItemUploadStateChoices.READY
        placeholder.save(update_fields=["mimetype", "size", "upload_state", "updated_at"])
    except DatabaseError:
        default_storage.delete(placeholder.file_key)
        raise

    return placeholder


def convert_item(source_item, user):
    """Prepare and run a conversion synchronously.

    Used by tests and any call site that wants the new converted item right away
    instead of going through the celery task.
    """
    placeholder = prepare_conversion(source_item, user)
    return perform_conversion(source_item, placeholder, user)
