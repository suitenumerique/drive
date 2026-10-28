"""Tests for the delete_orphan_objects command."""

from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

import pytest
from botocore.exceptions import ClientError

from core import factories, models
from core.management.commands import delete_orphan_objects

pytestmark = pytest.mark.django_db

OLD = timezone.now() - timedelta(days=7)
RECENT = timezone.now() - timedelta(hours=1)


class FakeBucket:
    """A versioned bucket: its listing comes in pages of two entries, to cross page edges."""

    def __init__(self):
        self.versions = []
        self.markers = []
        self.deleted = []

    def put(self, key, when=OLD, size=10):
        """A new version of `key`."""
        self.versions.append(
            {"Key": key, "VersionId": f"v{len(self.versions)}", "LastModified": when, "Size": size}
        )

    def hide(self, key, when=OLD):
        """A delete without a version id: a marker over the past versions."""
        self.markers.append(
            {"Key": key, "VersionId": f"m{len(self.markers)}", "LastModified": when}
        )

    def get_paginator(self, name):
        """The listing of versions, the only one the command uses."""
        assert name == "list_object_versions"
        return self

    def paginate(self, Bucket, Prefix):  # pylint: disable=invalid-name
        """Pages of the entries under the prefix, in key order, versions and markers apart."""
        assert Bucket == "bucket"
        entries = sorted(
            [("Versions", entry) for entry in self.versions if entry["Key"].startswith(Prefix)]
            + [
                ("DeleteMarkers", entry)
                for entry in self.markers
                if entry["Key"].startswith(Prefix)
            ],
            key=lambda pair: pair[1]["Key"],
        )
        for start in range(0, len(entries), 2):
            page = {}
            for kind, entry in entries[start : start + 2]:
                page.setdefault(kind, []).append(entry)
            yield page

    def head_object(self, Bucket, Key):  # pylint: disable=invalid-name
        """The latest version of `Key`, a 404 when it has none or is hidden by a marker."""
        assert Bucket == "bucket"
        entries = [entry for entry in [*self.versions, *self.markers] if entry["Key"] == Key]
        if not entries or entries[-1] in self.markers:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return entries[-1]

    def delete_object(self, Bucket, Key, VersionId):  # pylint: disable=invalid-name
        """Records a permanent deletion of one version."""
        assert Bucket == "bucket"
        self.deleted.append((Key, VersionId))


@pytest.fixture(name="bucket")
def fixture_bucket():
    """The fake bucket, standing for the default storage's."""
    bucket = FakeBucket()
    with mock.patch(
        "core.management.commands.delete_orphan_objects.s3", return_value=(bucket, "bucket")
    ):
        yield bucket


def old_file(filename, **kwargs):
    """A file item last changed a week ago, older than any delay the tests use."""
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename=filename, **kwargs)
    models.Item.objects.filter(pk=item.pk).update(updated_at=OLD)
    item.refresh_from_db()
    return item


def run(**options):
    """Run the command, returning what it printed."""
    out = StringIO()
    call_command("delete_orphan_objects", stdout=out, **options)
    return out.getvalue()


def test_delete_orphan_objects_lists_by_default_and_deletes_every_version_on_request(bucket):
    """An upload no item points to (a stopped import): listed, then gone with its versions."""
    item = old_file("facture.pdf")
    bucket.put(item.file_key)
    orphan = f"item/{item.pk}/3f1c2d9e-0000-4000-8000-000000000000/facture.pdf"
    bucket.put(orphan)
    bucket.put(orphan)

    output = run()

    assert output.splitlines() == [orphan, "Found 1 orphan object(s), 20 bytes."]
    assert not bucket.deleted

    output = run(delete=True)

    assert output.splitlines()[-1] == "Deleted 1 orphan object(s), 20 bytes."
    assert sorted(bucket.deleted) == [(orphan, "v1"), (orphan, "v2")]


def test_delete_orphan_objects_finds_a_key_deleted_without_its_versions(bucket):
    """The ciphertext a switch left as past versions behind a delete marker."""
    item = old_file("new/plain.pdf")
    old_key = f"item/{item.pk}/sealed.pdf"
    bucket.put(old_key)
    bucket.hide(old_key)
    bucket.put(item.file_key)

    run(delete=True)

    assert sorted(bucket.deleted) == [(old_key, "m0"), (old_key, "v0")]


def test_delete_orphan_objects_leaves_recent_referenced_and_foreign_keys(bucket):
    """A fresh upload, any item's file (trashed included), anything outside item/<uuid>/."""
    trashed = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, filename="old.pdf", deleted_at=timezone.now()
    )
    bucket.put(trashed.file_key)
    bucket.put(f"item/{trashed.pk}/pending-upload/new.pdf", when=RECENT)
    bucket.put("item/not-a-uuid/file.pdf")
    bucket.put("previews/whatever.png")

    output = run(delete=True)

    assert output.splitlines() == ["Deleted 0 orphan object(s), 0 bytes."]
    assert not bucket.deleted


def test_delete_orphan_objects_honours_the_delay(bucket):
    """--older-than-hours moves the line between an upload in flight and an orphan."""
    item = old_file("a.pdf")
    bucket.put(item.file_key)
    orphan = f"item/{item.pk}/left/a.pdf"
    bucket.put(orphan, when=RECENT)

    assert "Found 0 orphan" in run()
    assert run(older_than_hours=0).splitlines()[0] == orphan


def test_delete_orphan_objects_deletes_the_keys_of_an_item_gone_from_the_database(bucket):
    """No row any more: nothing can be the item's file but what the rows say."""
    orphan = "item/7c9e6679-7425-40de-944b-e07fc1f90ae7/sealed.pdf"
    bucket.put(orphan)

    run(delete=True)

    assert bucket.deleted == [(orphan, "v0")]


def test_delete_orphan_objects_keeps_the_only_copy_of_a_renamed_file(bucket):
    """
    The rename saved the new name, then the copy to it failed: the old key is the
    file, and it stays as long as the item's own key holds nothing.
    """
    item = old_file("renamed.pdf")
    previous = f"item/{item.pk}/before-the-rename.pdf"
    bucket.put(previous)

    assert "Deleted 0 orphan" in run(delete=True)
    assert not bucket.deleted

    bucket.put(item.file_key)
    run(delete=True)

    assert bucket.deleted == [(previous, "v0")]


def test_delete_orphan_objects_waits_for_an_item_changed_recently(bucket):
    """A rename in progress: the item changed within the delay, its old key waits too."""
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="renamed.pdf")
    bucket.put(item.file_key)
    bucket.put(f"item/{item.pk}/before-the-rename.pdf")

    assert "Deleted 0 orphan" in run(delete=True)
    assert not bucket.deleted


def test_delete_orphan_objects_asks_again_before_each_delete(bucket):
    """An item pointing to a key since its batch was read keeps it."""
    item = old_file("facture.pdf")
    bucket.put(item.file_key)
    switched_to = f"item/{item.pk}/3f1c2d9e-0000-4000-8000-000000000000/facture.pdf"
    bucket.put(switched_to)

    real = delete_orphan_objects.referenced
    calls = []

    def referenced(keys):
        calls.append(keys)
        # The re-check, after the listing: the item has switched to the new key.
        return {switched_to} if keys == [switched_to] else real(keys)

    with mock.patch.object(delete_orphan_objects, "referenced", side_effect=referenced):
        output = run(delete=True)

    assert calls == [[switched_to]]
    assert output.splitlines() == ["Deleted 0 orphan object(s), 0 bytes."]
    assert not bucket.deleted


def test_delete_orphan_objects_against_the_real_versioned_bucket():
    """
    On MinIO, as deployed: a hidden orphan loses its versions and marker, the file
    an item points to and its own past versions stay.
    """
    client = default_storage.connection.meta.client
    bucket = default_storage.bucket_name
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="kept.pdf")
    orphan = f"item/{item.pk}/0d0e0f00-0000-4000-8000-000000000000/sealed.pdf"

    client.put_object(Bucket=bucket, Key=item.file_key, Body=b"v1")
    client.put_object(Bucket=bucket, Key=item.file_key, Body=b"v2")
    client.put_object(Bucket=bucket, Key=orphan, Body=b"ciphertext")
    client.delete_object(Bucket=bucket, Key=orphan)

    def entries(key):
        listing = client.list_object_versions(Bucket=bucket, Prefix=key)
        return [
            entry
            for entry in [*listing.get("Versions", []), *listing.get("DeleteMarkers", [])]
            if entry["Key"] == key
        ]

    assert len(entries(orphan)) == 2

    output = StringIO()
    # Only this item's keys: the bucket is shared with the other tests, running in parallel.
    with mock.patch(
        "core.management.commands.delete_orphan_objects.LISTING_PREFIX", f"item/{item.pk}/"
    ):
        call_command("delete_orphan_objects", delete=True, older_than_hours=0, stdout=output)

    assert orphan in output.getvalue().splitlines()
    assert not entries(orphan)
    assert len(entries(item.file_key)) == 2
