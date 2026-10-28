"""
A batch recovery from end to end on fixed, really encrypted data, without a browser:
the trees of `core/tests/maintenance_fixture` (written with the encryption service's
code, see its `generate.mts`) are exported, decrypted as the maintenance tool would
(from the fixture's plaintexts), imported, then read back through the API.

What drifts on Drive's side (the export's lines, how the import reads the tool's
output) fails here on every run. The tool itself is run by the opt-in e2e test,
`maintenance-recovery.spec.ts`.
"""

import base64
import json
import re
from io import StringIO
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management import call_command

import pytest
import requests
from rest_framework.test import APIClient

from core import factories, models
from core.tests import maintenance_fixture

pytestmark = pytest.mark.django_db

FIXTURE = maintenance_fixture.load()
DEV_ROOT = FIXTURE["maintenance"]["roots"][0]
OTHER_ROOT = FIXTURE["otherOrganization"]["roots"][0]
ROWS = {entry["id"]: entry for entry in FIXTURE["items"]}
BASE64 = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _manifest(folder):
    return [json.loads(line) for line in (folder / "manifest.ndjson").read_text().splitlines()]


def _export(owner, output):
    maintenance_fixture.seed(owner)
    call_command(
        "maintenance_export",
        "--output",
        str(output),
        "--fingerprint",
        FIXTURE["maintenance"]["fingerprint"],
        stdout=StringIO(),
    )
    return _manifest(output)


def _decrypt_as_the_tool(export_dir, decrypted_dir):
    """
    The maintenance tool's decrypted copy (integration.mdx, "What comes back"): every
    line without its keys, product fields passed through, each `file` holding the
    plaintext.
    """
    lines = []
    for line in _manifest(export_dir):
        line.pop("maintenanceKey", None)
        line.pop("wrappedKey", None)
        if "file" in line:
            target = decrypted_dir / line["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(maintenance_fixture.plaintext(line["id"]))
        lines.append(line)
    decrypted_dir.mkdir(parents=True, exist_ok=True)
    (decrypted_dir / "manifest.ndjson").write_text(
        "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines)
    )


def _identity(item):
    """The stored version of an item's file, as the export records it."""
    head = default_storage.connection.meta.client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )
    identity = {"objectEtag": head["ETag"]}
    if head.get("VersionId"):
        identity["objectVersionId"] = head["VersionId"]
    return identity


def _download(client, item_id):
    """A file's bytes as a browser gets them: the item's url, authorized by media-auth."""
    response = client.get(f"/api/v1.0/items/{item_id}/")
    assert response.status_code == 200
    url = response.json()["url"]

    auth = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=url)
    assert auth.status_code == 200

    key = unquote(urlparse(url).path).removeprefix(settings.MEDIA_URL)
    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    content = requests.get(
        f"{settings.AWS_S3_ENDPOINT_URL}/{default_storage.bucket_name}/{key}",
        headers={
            "authorization": auth["Authorization"],
            "x-amz-date": auth["x-amz-date"],
            "x-amz-content-sha256": auth["x-amz-content-sha256"],
            "Host": f"{s3_url.hostname}:{s3_url.port}",
        },
        timeout=5,
    )
    assert content.status_code == 200
    return content.content


def _assert_export(tmp_path, lines):
    """The DEV key's tree, whole, with the stored copies and the ciphertext byte for byte."""
    items = {str(item.pk): item for item in models.Item.objects.filter(pk__in=ROWS)}
    expected = []

    for line in lines:
        row = ROWS[line["id"]]
        item = items[line["id"]]
        entry = {
            "id": row["id"],
            "type": row["type"],
            "title": row["title"],
            "updatedAt": item.updated_at.isoformat(),
        }
        if row["parent"] is None:
            entry["maintenanceKey"] = row["maintenance_wrapped_item_key"]
        else:
            entry["parent"] = row["parent"]
            entry["wrappedKey"] = row["encrypted_symmetric_key"]
        if row["type"] == "file":
            entry["file"] = f"files/{row['id']}"
            entry |= _identity(item)
            assert (tmp_path / entry["file"]).read_bytes() == maintenance_fixture.stored_object(
                item.file_key
            )
        expected.append(entry)

    assert lines == expected
    # The DEV key's tree only, every item of it, parents before children.
    assert sorted(line["id"] for line in lines) == sorted(
        item_id for item_id in ROWS if item_id != OTHER_ROOT
    )
    assert lines[0]["id"] == DEV_ROOT
    seen = set()
    for line in lines:
        assert line.get("parent") is None or line["parent"] in seen
        seen.add(line["id"])
        for name in ("maintenanceKey", "wrappedKey"):
            assert name not in line or BASE64.match(line[name]), name
    # The copy names the DEV key: the tool opens it, and sets the others aside.
    copy = base64.b64decode(lines[0]["maintenanceKey"])
    assert copy[0] == 1
    fingerprint = "1" + str(int.from_bytes(copy[1:17], "big")).zfill(39)
    assert fingerprint == FIXTURE["maintenance"]["fingerprint"]
    assert sorted(path.name for path in (tmp_path / "files").iterdir()) == sorted(
        line["id"] for line in lines if "file" in line
    )


def _assert_imported(owner):
    """
    Decrypted and imported, the DEV tree reads in plaintext through the API, the
    other stays sealed.
    """
    client = APIClient()
    client.force_login(owner)

    root = client.get(f"/api/v1.0/items/{DEV_ROOT}/").json()
    assert root["is_encrypted"] is False
    children = client.get(f"/api/v1.0/items/{DEV_ROOT}/children/").json()["results"]
    assert {child["title"]: child["is_encrypted"] for child in children} == {
        "Annexes": False,
        "compte-rendu.pdf": False,
    }

    for item_id, mimetype in (
        ("d7e00000-0000-4000-8000-000000000003", "image/png"),
        ("d7e00000-0000-4000-8000-000000000004", "application/pdf"),
    ):
        item = client.get(f"/api/v1.0/items/{item_id}/").json()
        plaintext = maintenance_fixture.plaintext(item_id)
        assert item["is_encrypted"] is False
        assert item["mimetype"] == mimetype
        assert item["size"] == len(plaintext)
        assert _download(client, item_id) == plaintext

    assert FIXTURE["minutesText"].encode() in maintenance_fixture.plaintext(
        "d7e00000-0000-4000-8000-000000000004"
    )
    assert not models.Item.objects.filter(pk__in=ROWS, is_encrypted=True).exclude(pk=OTHER_ROOT)
    assert not models.ItemEncryptionKeyWrap.objects.filter(item_id=DEV_ROOT).exists()

    other = models.Item.objects.get(pk=OTHER_ROOT)
    assert other.is_encrypted
    assert other.maintenance_wrapped_item_key == ROWS[OTHER_ROOT]["maintenance_wrapped_item_key"]
    assert default_storage.open(other.file_key).read() == maintenance_fixture.stored_object(
        other.file_key
    )


def test_maintenance_fixture_from_export_to_plaintext(tmp_path):
    """
    One test, not several: the fixture's object keys are fixed, and the storage is
    shared by the test workers, which would delete each other's.
    """
    owner = factories.UserFactory(email="seeded@example.com")
    _assert_export(tmp_path / "export", _export("seeded@example.com", tmp_path / "export"))
    _decrypt_as_the_tool(tmp_path / "export", tmp_path / "decrypted")

    output = StringIO()
    call_command("maintenance_import", str(tmp_path / "decrypted"), stdout=output)

    assert output.getvalue() == "Switched 1 tree(s) to plaintext.\n"
    _assert_imported(owner)

    # Seeding again (an e2e run after an interrupted one) replaces the trees.
    maintenance_fixture.seed(owner)
    assert models.Item.objects.filter(pk__in=ROWS, is_encrypted=True).count() == len(ROWS)

    maintenance_fixture.remove()
    assert not models.Item.objects.filter(pk__in=ROWS).exists()
    # Nothing left behind, not even the ciphertext the import kept as past versions.
    client = default_storage.connection.meta.client
    for item_id in ROWS:
        listing = client.list_object_versions(
            Bucket=default_storage.bucket_name, Prefix=f"item/{item_id}/"
        )
        assert not listing.get("Versions") and not listing.get("DeleteMarkers")
