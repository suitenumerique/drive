"""
Encrypted Drive trees for the batch recovery tests, loaded from `drive-trees.json`,
which `generate.mts` beside it writes with the encryption service's code (see its
header): the rows and objects exactly as Drive's frontend stores them, the escrow
copies for the development maintenance key, and the plaintexts they hold.

Not a test module: `test_maintenance_fixture.py` seeds it for the always-on tests,
and the e2e suite's `maintenance-recovery.spec.ts` seeds it for its user through
`python manage.py shell -c "from core.tests.maintenance_fixture import seed; seed('<email>')"`.
"""

import base64
import json
from functools import cache
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from core import models

FIXTURE_FILE = Path(__file__).with_name("drive-trees.json")


@cache
def load():
    """The fixture as written by `generate.mts`."""
    return json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))


def plaintext(item_id):
    """The bytes an item's file decrypts to."""
    return base64.b64decode(load()["plaintexts"][str(item_id)])


def stored_object(key):
    """The ciphertext the fixture stores at an object key."""
    return base64.b64decode(load()["objects"][key])


def item_ids():
    """The ids of every item of the fixture, both trees."""
    return [entry["id"] for entry in load()["items"]]


def remove():
    """
    Delete the fixture's items and every object under them, plaintext uploads
    included, every version: in a versioned bucket a delete without a version id
    only hides an object, its bytes left in its past versions.
    """
    client = default_storage.connection.meta.client
    bucket = default_storage.bucket_name

    for item_id in item_ids():
        for page in client.get_paginator("list_object_versions").paginate(
            Bucket=bucket, Prefix=f"item/{item_id}/"
        ):
            for entry in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]:
                client.delete_object(Bucket=bucket, Key=entry["Key"], VersionId=entry["VersionId"])

    models.Item.objects.filter(pk__in=item_ids()).delete()


@transaction.atomic
def seed(owner):
    """
    Create the fixture's trees for `owner` (a user, or the email of an existing one),
    replacing any earlier seed of them, and upload their encrypted objects. Returns
    the items by id.
    """
    if isinstance(owner, str):
        owner = models.User.objects.get(email=owner)

    remove()
    fixture = load()
    items = {}

    for entry in fixture["items"]:
        fields = {name: value for name, value in entry.items() if name not in ("parent",)}
        upload_state = fields.pop("upload_state", None)
        parent = items[entry["parent"]] if entry["parent"] else None
        item = models.Item.objects.create_child(parent=parent, creator=owner, **fields)

        # A file's first save forces the upload to pending: the fixture's is finished.
        if upload_state:
            item.upload_state = upload_state
            item.save(update_fields=["upload_state"])

        items[entry["id"]] = item

    for entry in fixture["accesses"]:
        models.ItemAccess.objects.create(user=owner, **entry | {"item": items[entry["item"]]})

    for key, data in fixture["objects"].items():
        default_storage.save(key, ContentFile(base64.b64decode(data)))

    return items
