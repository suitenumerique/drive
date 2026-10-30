"""Deleting stored objects for good."""

import logging

from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

# The most keys one DeleteObjects request takes.
DELETE_BATCH_SIZE = 1000


def delete_every_version(key):
    """
    Delete a key with all its versions and delete markers. In a versioned bucket a
    delete without a version id only hides the key: its bytes stay in its past
    versions, which is no deletion for the plaintext of a file just encrypted. In an
    unversioned bucket the listing holds the one "null" version, deleted the same way.
    """
    client = default_storage.connection.meta.client
    bucket = default_storage.bucket_name

    entries = [
        {"Key": key, "VersionId": entry["VersionId"]}
        for page in client.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=key)
        for entry in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]
        # The prefix also matches longer keys.
        if entry["Key"] == key
    ]

    for start in range(0, len(entries), DELETE_BATCH_SIZE):
        response = client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": entries[start : start + DELETE_BATCH_SIZE], "Quiet": True},
        )
        for error in response.get("Errors", []):
            logger.warning(
                "Failed to delete version %s of %s: %s",
                error.get("VersionId"),
                key,
                error.get("Message"),
            )
