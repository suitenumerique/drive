"""Render document thumbnails through the configured WOPI provider."""

import logging
from io import BytesIO

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.utils import timezone

from PIL import Image

from core import models
from wopi.conversion.backends.collabora import CollaboraConversionBackend
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend
from wopi.conversion.exceptions import ConversionProviderError
from wopi.tasks.configure_wopi import configure_wopi_clients
from wopi.utils import get_wopi_configuration

logger = logging.getLogger(__name__)

BACKENDS = {
    "collabora": CollaboraConversionBackend,
    "onlyoffice": OnlyOfficeConversionBackend,
}

# Only one refresh of a stale WOPI configuration is queued in this many seconds.
CONFIGURATION_REFRESH_INTERVAL = 300
CONFIGURATION_REFRESH_KEY = "wopi_thumbnail_configuration_refresh"

# The frontend shows these images through their own preview, they need no thumbnail.
BROWSER_IMAGE_MIMETYPES = {
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/svg+xml",
    "image/webp",
}


def thumbnail_clients():
    """Yield (client, ThumbnailServiceUrl) of the WOPI clients opting in, in order."""
    for client in settings.WOPI_CLIENTS:
        options = settings.WOPI_CLIENTS_CONFIGURATION.get(client, {}).get("options", {})
        thumbnail_service_url = options.get("ThumbnailServiceUrl")
        if thumbnail_service_url and client in BACKENDS:
            yield client, thumbnail_service_url


def resolve_thumbnail_backend(item):
    """Return a backend for the first client opting in that can render the item.

    Raise ConversionProviderError, which the render task retries on, while the formats a
    client renders are unknown: its configuration was cached before they were recorded,
    or its discovery has not succeeded yet. A refresh of the configuration is queued.
    """
    configuration = get_wopi_configuration()
    extension = item.extension.lower() if item.extension else None
    for client, thumbnail_service_url in thumbnail_clients():
        renderable = configuration.get(client, {}).get("renderable")
        if renderable is None:
            if cache.add(CONFIGURATION_REFRESH_KEY, True, timeout=CONFIGURATION_REFRESH_INTERVAL):
                logger.warning(
                    "The formats WOPI client %s renders are unknown, refreshing its configuration",
                    client,
                )
                configure_wopi_clients.delay()
            raise ConversionProviderError(f"Formats rendered by WOPI client {client} are unknown")
        if extension in renderable.get("extensions", ()) or item.mimetype in renderable.get(
            "mimetypes", ()
        ):
            return BACKENDS[client](convert_service_url=thumbnail_service_url)
    return None


def is_thumbnail_pending(item, configuration):
    """Return whether a ready item has no thumbnail yet but a client renders it."""
    if (
        item.filename is None
        or item.thumbnail_updated_at is not None
        or item.upload_state != models.ItemUploadStateChoices.READY
        or item.mimetype in BROWSER_IMAGE_MIMETYPES
        or (item.size or 0) > settings.WOPI_THUMBNAIL_MAX_FILE_SIZE
    ):
        return False
    extension = item.extension.lower() if item.extension else None
    for client, _thumbnail_service_url in thumbnail_clients():
        renderable = configuration.get(client, {}).get("renderable") or {}
        if extension in renderable.get("extensions", ()) or item.mimetype in renderable.get(
            "mimetypes", ()
        ):
            return True
    return False


def generate_thumbnail(item):
    """Render, resize and store the item thumbnail.

    Return False when not applicable, or when a render started later already won.
    """
    if (
        item.upload_state != models.ItemUploadStateChoices.READY
        or item.mimetype in BROWSER_IMAGE_MIMETYPES
        or (item.size or 0) > settings.WOPI_THUMBNAIL_MAX_FILE_SIZE
    ):
        return False
    backend = resolve_thumbnail_backend(item)
    if backend is None:
        return False

    # Stamp the render with its start, when the backend reads the file: when renders
    # overlap, the one reading the latest save wins whatever order they finish in.
    # Truncated to the key precision, so that a render that lost never owns the key of
    # the one that won.
    now = timezone.now()
    rendered_at = now.replace(microsecond=now.microsecond // 1000 * 1000)
    size = settings.WOPI_THUMBNAIL_SIZE
    image = Image.open(backend.thumbnail(item, size))
    image.thumbnail((size, size))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    item.thumbnail_updated_at = rendered_at
    thumbnail_key = item.thumbnail_key
    # save() never overwrites, it would suffix the key instead.
    default_storage.delete(thumbnail_key)
    default_storage.save(thumbnail_key, ContentFile(buffer.getvalue()))
    # update() skips the post_save signal, a new thumbnail is no reason to reindex the item.
    is_latest = (
        models.Item.objects.filter(pk=item.pk)
        .filter(Q(thumbnail_updated_at__isnull=True) | Q(thumbnail_updated_at__lte=rendered_at))
        .update(thumbnail_updated_at=rendered_at)
    )
    if not is_latest:
        default_storage.delete(thumbnail_key)
        return False

    # Also drop the renders of overlapping runs that lost, the folder holds no other files.
    folder = item.thumbnail_folder
    _dirs, files = default_storage.listdir(folder)
    for filename in files:
        if _thumbnail_time(filename) < _thumbnail_time(thumbnail_key):
            default_storage.delete(f"{folder}/{filename}")
    return True


def _thumbnail_time(key):
    """Return the render time in milliseconds a thumbnail key is versioned with."""
    try:
        return int(key.rsplit("/", 1)[-1].removesuffix(".png"))
    except ValueError:
        return -1
