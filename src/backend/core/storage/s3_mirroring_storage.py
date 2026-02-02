"""S3 storage mirroring files on multiple S3 buckets."""

from storages.backends.s3 import S3Storage

from core.services.mirror import mirror_item_from_file_key

# pylint: disable=abstract-method


class S3MirroringStorage(S3Storage):
    """S3 storage mirroring files on multiple S3 buckets."""

    def save(self, name, content, max_length=None):
        """Dispatch a celery task to mirror the file on the other S3 buckets."""
        name = super().save(name, content, max_length)

        mirror_item_from_file_key(name)
        return name
