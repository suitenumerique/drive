"""Services around item versioning.

An item version is a snapshot of a file's content stored in object storage
before it gets overwritten. This module handles snapshotting, restoring,
deleting and enforcing the maximum number of stored versions per item.
"""

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db.models import Max

from core import models

# Any item type other than FILE cannot be versioned (folders never are).
VERSIONABLE_UPLOAD_STATES = {
    models.ItemUploadStateChoices.READY,
    models.ItemUploadStateChoices.ANALYZING,
}


def _s3():
    """Return the low-level S3 client backing the default storage."""
    return default_storage.connection.meta.client


def _bucket():
    """Return the bucket name used by the default storage."""
    return default_storage.bucket_name


def next_version_number(item):
    """Return the next available version number for an item."""
    last = item.versions.aggregate(max=Max("version_number"))["max"]
    return (last or 0) + 1


def snapshot_version(item, created_by=None):
    """Store the current file content of ``item`` as a new stored version.

    Returns the created ``ItemVersion``, or ``None`` if the item is not a file
    or is not in a state where its content can be versioned yet.
    """
    if item.type != models.ItemTypeChoices.FILE or item.filename is None:
        return None
    if item.upload_state not in VERSIONABLE_UPLOAD_STATES:
        return None
    if not default_storage.exists(item.file_key):
        return None

    version = models.ItemVersion.objects.create(
        item=item,
        filename=item.filename,
        mimetype=item.mimetype,
        size=item.size,
        version_number=next_version_number(item),
        created_by=created_by,
    )
    _s3().copy_object(
        Bucket=_bucket(),
        Key=version.file_key,
        CopySource={"Bucket": _bucket(), "Key": item.file_key},
    )
    enforce_max_versions(item)
    return version


def enforce_max_versions(item):
    """Delete the oldest stored versions above the configured cap."""
    max_versions = settings.MAX_ITEM_VERSIONS
    if max_versions < 1:
        raise ValueError("MAX_ITEM_VERSIONS must be greater than or equal to 1")
    versions = list(item.versions.order_by("version_number"))
    for version in versions[:-max_versions]:
        delete_version(version)


def restore_version(version, created_by=None):
    """Restore a stored version as the live content of its item.

    The current content is snapshotted first so nothing is lost, then the
    restored bytes become the file's current content. The file keeps its own
    filename (restoring a historical filename could collide with an existing
    sibling), so only the content, size and mimetype are restored. The restored
    record is dropped as its content is now the live file.
    """
    item = version.item
    snapshot_version(item, created_by=created_by)
    _s3().copy_object(
        Bucket=_bucket(),
        Key=item.file_key,
        CopySource={"Bucket": _bucket(), "Key": version.file_key},
    )
    item.size = version.size
    item.mimetype = version.mimetype
    item.save(update_fields=["size", "mimetype", "updated_at"])
    delete_version(version)
    enforce_max_versions(item)


def discard_current_version(item):
    """Drop the live content and promote the newest stored version.

    The current bytes are not snapshotted. Returns the promoted version, or
    None when the file has no stored version to take its place.
    """
    version = item.versions.order_by("-version_number").first()
    if version is None:
        return None
    _s3().copy_object(
        Bucket=_bucket(),
        Key=item.file_key,
        CopySource={"Bucket": _bucket(), "Key": version.file_key},
    )
    item.size = version.size
    item.mimetype = version.mimetype
    item.save(update_fields=["size", "mimetype", "updated_at"])
    delete_version(version)
    return version


def delete_version(version, keep_storage=False):
    """Delete a stored version (and, by default, its storage bytes)."""
    if not keep_storage:
        _s3().delete_object(Bucket=_bucket(), Key=version.file_key)
    version.delete()


def replacement_cache_key(item_id):
    """Cache key remembering the snapshot to restore if a replacement fails."""
    return f"item-replace-upload:{item_id}"


def mark_replacement(item, version):
    """Remember which snapshot to restore if this replacement upload fails."""
    cache.set(
        replacement_cache_key(item.pk),
        "" if version is None else str(version.pk),
        timeout=settings.AWS_S3_UPLOAD_POLICY_EXPIRATION,
    )


def clear_replacement(item):
    """Forget a replacement marker once the new content is accepted."""
    cache.delete(replacement_cache_key(item.pk))


def abort_replacement(item):
    """Restore the snapshotted content of a failed replacement.

    Returns True when this pending upload was a replacement, so the item is
    kept. Returns False when there is no marker, so the caller can delete a
    brand-new upload instead.
    """
    marker = cache.get(replacement_cache_key(item.pk))
    if marker is None:
        return False

    cache.delete(replacement_cache_key(item.pk))
    version = models.ItemVersion.objects.filter(pk=marker, item=item).first() if marker else None
    if version is None:
        item.upload_state = models.ItemUploadStateChoices.READY
        item.save(update_fields=["upload_state", "updated_at"])
        return True

    _s3().copy_object(
        Bucket=_bucket(),
        Key=item.file_key,
        CopySource={"Bucket": _bucket(), "Key": version.file_key},
    )
    item.size = version.size
    item.mimetype = version.mimetype
    item.upload_state = models.ItemUploadStateChoices.READY
    item.save(update_fields=["size", "mimetype", "upload_state", "updated_at"])
    delete_version(version)
    return True
