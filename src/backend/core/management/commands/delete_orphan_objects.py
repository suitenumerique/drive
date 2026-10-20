"""Delete the objects no item points to any more."""

import re
from datetime import timedelta
from itertools import islice

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from botocore.exceptions import ClientError

from core.models import Item

PREFIX = "item/"
# Where the listing starts: the whole of `item/`, narrowed only by tests sharing a bucket.
LISTING_PREFIX = PREFIX
ITEM_KEY = re.compile(r"^item/([0-9a-f-]{36})/(.+)$")
BATCH = 500


def s3():
    """The client and bucket of the default storage."""
    return default_storage.connection.meta.client, default_storage.bucket_name


def objects(client, bucket):
    """
    Every key under `item/` with all its versions and delete markers, key after key.
    A delete without a version id only hides a key in a versioned bucket: its bytes
    stay in its past versions, so a key whose latest entry is a delete marker is
    listed too.
    """
    current, entries = None, []

    for page in client.get_paginator("list_object_versions").paginate(
        Bucket=bucket, Prefix=LISTING_PREFIX
    ):
        for entry in sorted(
            [*page.get("Versions", []), *page.get("DeleteMarkers", [])],
            key=lambda entry: entry["Key"],
        ):
            if entry["Key"] != current:
                if current is not None:
                    yield current, entries
                current, entries = entry["Key"], []
            entries.append(entry)

    if current is not None:
        yield current, entries


def _ids(keys):
    return {match.group(1) for match in map(ITEM_KEY.match, keys) if match}


def referenced(keys):
    """The keys among `keys` that are the file key of an item, whatever its state."""
    rows = Item.objects.filter(pk__in=_ids(keys), filename__isnull=False).values_list(
        "pk", "filename"
    )

    return {f"{PREFIX}{pk}/{filename}" for pk, filename in rows}


def exists(client, bucket, key):
    """Whether `key` holds an object (its latest version is not a delete marker)."""
    try:
        client.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
    return True


def orphans(client, bucket, older_than):
    """
    The keys no item points to and untouched for `older_than`, with their entries.
    The delay leaves alone an upload whose item is about to point to it (the
    encryption of a file and the import of a batch recovery write the new object
    before switching the item to it).

    A key under an item that still exists may hold that item's only bytes: a rename
    saves the new name before copying the object to it, so after a failed copy the
    old key is the file. Such a key goes only once the item's own key exists and the
    item has not changed for `older_than` either.
    """
    cutoff = timezone.now() - older_than
    listing = objects(client, bucket)

    while batch := list(islice(listing, BATCH)):
        rows = {
            str(pk): (filename, updated_at)
            for pk, filename, updated_at in Item.objects.filter(
                pk__in=_ids([key for key, _ in batch])
            ).values_list("pk", "filename", "updated_at")
        }

        for key, entries in batch:
            match = ITEM_KEY.match(key)
            # Never a key this command does not understand.
            if not match:
                continue
            if max(entry["LastModified"] for entry in entries) >= cutoff:
                continue

            item_id = match.group(1)
            if item_id in rows:
                filename, updated_at = rows[item_id]
                current = f"{PREFIX}{item_id}/{filename}" if filename else None
                if (
                    key == current
                    or current is None
                    or updated_at >= cutoff
                    or not exists(client, bucket, current)
                ):
                    continue

            yield key, entries


class Command(BaseCommand):
    """List, or delete, the objects of the bucket no item points to."""

    help = (
        "Find the objects under item/ that no item points to: left by a process stopped "
        "between an upload and the database change that used it (the encryption of a "
        "file, a batch recovery import), or deleted without their past versions. Lists "
        "them; --delete removes every version of each."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-hours",
            type=int,
            default=48,
            help="Leave alone objects written more recently than this (48 by default)",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete them, every version; without it, only list them",
        )

    def handle(self, *args, **options):
        client, bucket = s3()
        count = size = 0

        for key, entries in orphans(client, bucket, timedelta(hours=options["older_than_hours"])):
            # Asked again right before the delete: its item may have come to point to
            # it since the batch it was listed in was read.
            if options["delete"] and key in referenced([key]):
                continue

            count += 1
            size += sum(entry.get("Size", 0) for entry in entries)
            self.stdout.write(key)

            if options["delete"]:
                for entry in entries:
                    client.delete_object(Bucket=bucket, Key=key, VersionId=entry["VersionId"])

        verb = "Deleted" if options["delete"] else "Found"
        self.stdout.write(f"{verb} {count} orphan object(s), {size} bytes.")
