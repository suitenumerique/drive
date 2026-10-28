"""Tests for the maintenance_export, maintenance_import and maintenance_rotate commands."""

import base64
import json
import os
import re
from io import StringIO
from unittest import mock
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.query import QuerySet
from django.utils import timezone

import pytest

from core import factories, models
from core.services import maintenance_escrow

pytestmark = pytest.mark.django_db

ORGANIZATION_A = bytes(range(16))
ORGANIZATION_B = bytes(range(16, 32))


def _fingerprint(key_id):
    """The 40 digits the tool shows for a key id: the scheme digit, then the id as a number."""
    return "1" + str(int.from_bytes(key_id, "big")).zfill(39)


INVOICE = b"%PDF-1.4\n% the invoice"


def _copy(key_id=ORGANIZATION_A):
    """A maintenance copy as the vault writes it: version byte, key id, then the wrap."""
    return base64.b64encode(bytes([1]) + key_id + os.urandom(1120)).decode()


COPY_A = _copy()


def _wrap():
    """A key wrapped by its parent's, as the vault writes it: nonce, key, tag."""
    return base64.b64encode(os.urandom(24 + 32 + 16)).decode()


def _root(*, maintenance_key=COPY_A, item_type=models.ItemTypeChoices.FOLDER, **kwargs):
    root = factories.ItemFactory(
        type=item_type,
        is_encrypted=True,
        encrypted_symmetric_key=None,
        maintenance_wrapped_item_key=maintenance_key,
        **kwargs,
    )
    access = factories.UserItemAccessFactory(item=root, role="owner")
    factories.ItemEncryptionKeyWrapFactory(item=root, user=access.user, wrapped_key=_wrap())
    return root


def _child(parent, *, item_type=models.ItemTypeChoices.FOLDER, title=None):
    extra = {}
    if item_type == models.ItemTypeChoices.FILE:
        # What an encrypted upload leaves: the ciphertext's type and size.
        extra = {"mimetype": "application/octet-stream", "size": 4242}
    return factories.ItemFactory(
        parent=parent,
        type=item_type,
        is_encrypted=True,
        encrypted_symmetric_key=_wrap(),
        **({"title": title} if title else {}),
        **extra,
    )


def _store(item, content):
    default_storage.save(item.file_key, ContentFile(content))


def _s3():
    return default_storage.connection.meta.client, default_storage.bucket_name


def _identity(item):
    """The stored version of an item's file, as the export records it."""
    client, bucket = _s3()
    head = client.head_object(Bucket=bucket, Key=item.file_key)
    identity = {"objectEtag": head["ETag"]}
    if head.get("VersionId"):
        identity["objectVersionId"] = head["VersionId"]
    return identity


def _tree():
    """A root folder, a subfolder, a file two levels down: the shape of a Drive tree."""
    root = _root(title="Budget 2027")
    annexes = _child(root, title="Annexes")
    invoice = _child(annexes, item_type=models.ItemTypeChoices.FILE, title="facture.pdf")
    _store(invoice, b"sealed invoice")
    return root, annexes, invoice


def _manifest(folder):
    return [json.loads(line) for line in (folder / "manifest.ndjson").read_text().splitlines()]


BASE64 = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _assert_valid_for_the_tool(folder):
    """The rules the maintenance tool applies to an export (its export-format.ts)."""
    lines = _manifest(folder)
    ids = {line["id"] for line in lines}
    files = set()

    assert len(ids) == len(lines)
    for line in lines:
        assert ("maintenanceKey" in line) != ("parent" in line)
        assert "wrappedKey" not in line or "parent" in line
        assert not ("content" in line and "file" in line)
        for name in ("maintenanceKey", "wrappedKey", "content"):
            assert name not in line or BASE64.match(line[name]), name
        assert "parent" not in line or line["parent"] in ids

        if "file" in line:
            path = line["file"]
            parts = path.split("/")
            assert not path.startswith("/")
            assert "\\" not in path
            assert all(part not in ("", ".", "..") for part in parts)
            assert path != "manifest.ndjson"
            assert parts[0].lower() != "other-keys"
            assert path.lower() not in files
            files.add(path.lower())
            assert (folder / path).is_file()


def _decrypt(export_dir, decrypted_dir, *, plaintexts, failed=()):
    """What the maintenance tool hands back: key fields dropped, plaintext at each `file`."""
    lines = []
    for line in _manifest(export_dir):
        line.pop("maintenanceKey", None)
        line.pop("wrappedKey", None)
        if line["id"] in failed:
            line.pop("file", None)
            line["error"] = "WRONG_SECRET_KEY: decryption failed"
        elif "file" in line:
            target = decrypted_dir / line["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(plaintexts[line["id"]])
        lines.append(line)
    decrypted_dir.mkdir(parents=True, exist_ok=True)
    (decrypted_dir / "manifest.ndjson").write_text(
        "".join(json.dumps(line) + "\n" for line in lines)
    )


def _objects(*items):
    """Every live object key under the given items."""
    client, bucket = _s3()
    keys = set()
    for item in items:
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=f"item/{item.pk}/"
        ):
            keys.update(entry["Key"] for entry in page.get("Contents", []))
    return keys


def _hard_delete(item):
    now = timezone.now()
    models.Item.objects.filter(pk=item.pk).update(
        deleted_at=now, ancestors_deleted_at=now, hard_deleted_at=now
    )


# ============================================================================
# maintenance_export
# ============================================================================


def test_maintenance_export_a_three_level_tree(tmp_path):
    """Every item of the tree, its keys chained from the root, the file streamed with its
    version."""
    root, annexes, invoice = _tree()

    # Chunks smaller than the file: the copy goes through several.
    with mock.patch.object(maintenance_escrow, "CHUNK_SIZE", 4):
        summary = maintenance_escrow.export(tmp_path)

    assert summary.trees == 1
    assert summary.files == 1
    assert _manifest(tmp_path) == [
        {
            "id": str(root.pk),
            "type": "folder",
            "title": "Budget 2027",
            "updatedAt": root.updated_at.isoformat(),
            "maintenanceKey": COPY_A,
        },
        {
            "id": str(annexes.pk),
            "type": "folder",
            "title": "Annexes",
            "updatedAt": annexes.updated_at.isoformat(),
            "parent": str(root.pk),
            "wrappedKey": annexes.encrypted_symmetric_key,
        },
        {
            "id": str(invoice.pk),
            "type": "file",
            "title": "facture.pdf",
            "updatedAt": invoice.updated_at.isoformat(),
            "parent": str(annexes.pk),
            "wrappedKey": invoice.encrypted_symmetric_key,
            "file": f"files/{invoice.pk}",
            **_identity(invoice),
        },
    ]
    assert (tmp_path / "files" / str(invoice.pk)).read_bytes() == b"sealed invoice"
    _assert_valid_for_the_tool(tmp_path)


def test_maintenance_export_keeps_an_inner_encrypted_tree_apart(tmp_path):
    """An encryption root inside another is a tree of its own, with its own copy."""
    outer, _annexes, _invoice = _tree()
    inner = _root(parent=outer, title="Inner", maintenance_key=_copy(ORGANIZATION_B))
    _child(inner, title="Inner child")

    maintenance_escrow.export(tmp_path)
    lines = _manifest(tmp_path)

    assert [line["title"] for line in lines if "maintenanceKey" in line] == ["Budget 2027", "Inner"]
    assert next(line for line in lines if line["title"] == "Inner child")["parent"] == str(inner.pk)
    _assert_valid_for_the_tool(tmp_path)


def test_maintenance_export_leaves_out_hard_deleted_descendants(tmp_path):
    """A purged item is not part of the tree any more."""
    _root_item, annexes, _invoice = _tree()
    gone = _child(annexes, item_type=models.ItemTypeChoices.FILE, title="gone.pdf")
    _store(gone, b"sealed")
    _hard_delete(gone)

    summary = maintenance_escrow.export(tmp_path)

    assert summary.items == 3
    assert str(gone.pk) not in {line["id"] for line in _manifest(tmp_path)}
    assert not (tmp_path / "files" / str(gone.pk)).exists()


def test_maintenance_export_only_the_trees_of_one_key(tmp_path):
    """--key-id matches bytes 2 to 17 of each copy, in SQL."""
    _tree()
    other = _root(title="Elsewhere", maintenance_key=_copy(ORGANIZATION_B))

    maintenance_escrow.export(tmp_path, key_id=ORGANIZATION_B.hex())

    assert [line["id"] for line in _manifest(tmp_path)] == [str(other.pk)]


def test_maintenance_export_refuses_a_malformed_key_id(tmp_path):
    """A key id is 32 hexadecimal characters, nothing else reaches the SQL."""
    with pytest.raises(ValueError):
        maintenance_escrow.export(tmp_path, key_id="1041813124")


def test_maintenance_export_command_takes_the_fingerprint(tmp_path):
    """--fingerprint takes the 40 digits as the tool groups them, never the key id in hex."""
    _tree()
    other = _root(title="Elsewhere", maintenance_key=_copy(ORGANIZATION_B))
    digits = _fingerprint(ORGANIZATION_B)

    call_command(
        "maintenance_export",
        "--output",
        str(tmp_path / "export"),
        "--fingerprint",
        " ".join(digits[i : i + 5] for i in range(0, 40, 5)),
        stdout=StringIO(),
    )

    assert [line["id"] for line in _manifest(tmp_path / "export")] == [str(other.pk)]

    for wrong in (ORGANIZATION_B.hex(), "1 0418", "2" + digits[1:], "1" + "9" * 39):
        with pytest.raises(CommandError, match="40 digits"):
            call_command(
                "maintenance_export", "--output", str(tmp_path / "other"), "--fingerprint", wrong
            )


def test_maintenance_export_refuses_a_folder_not_empty(tmp_path):
    """An earlier export's files would pass for this one's."""
    (tmp_path / "manifest.ndjson").write_text("")

    with pytest.raises(CommandError, match="is not empty"):
        call_command("maintenance_export", "--output", str(tmp_path), stdout=StringIO())


def test_maintenance_export_reports_trees_without_a_copy_and_missing_objects(tmp_path):
    """A tree no key can open is counted, a file missing from the storage is named."""
    _root(title="Before the escrow", maintenance_key=None)
    root = _root(title="Copied")
    lost = _child(root, item_type=models.ItemTypeChoices.FILE)

    output = StringIO()
    call_command("maintenance_export", "--output", str(tmp_path), stdout=output)

    assert "Exported 1 tree(s): 2 item(s), 0 file(s)." in output.getvalue()
    assert lost.file_key in output.getvalue()
    assert "1 tree(s) have no maintenance copy" in output.getvalue()
    assert "objectEtag" not in next(
        line for line in _manifest(tmp_path) if line["id"] == str(lost.pk)
    )


def test_maintenance_export_keys_only(tmp_path):
    """--keys-only: each root and its copy, nothing below it, no file written."""
    root, _annexes, _invoice = _tree()
    other = _root(title="Elsewhere", maintenance_key=_copy(ORGANIZATION_B))
    _root(title="Before the escrow", maintenance_key=None)

    output = StringIO()
    call_command("maintenance_export", "--output", str(tmp_path), "--keys-only", stdout=output)

    assert sorted(_manifest(tmp_path), key=lambda line: line["id"]) == sorted(
        [
            {"id": str(root.pk), "type": "folder", "maintenanceKey": COPY_A},
            {
                "id": str(other.pk),
                "type": "folder",
                "maintenanceKey": other.maintenance_wrapped_item_key,
            },
        ],
        key=lambda line: line["id"],
    )
    assert [path.name for path in tmp_path.iterdir()] == ["manifest.ndjson"]
    assert "Exported the copies of 2 encryption root(s)." in output.getvalue()
    assert "1 tree(s) have no maintenance copy" in output.getvalue()


def test_maintenance_export_keys_only_of_one_key(tmp_path):
    """--keys-only with --key-id: the copies to re-wrap when that key is replaced."""
    _tree()
    other = _root(title="Elsewhere", maintenance_key=_copy(ORGANIZATION_B), item_type="file")

    maintenance_escrow.export(tmp_path, key_id=ORGANIZATION_B.hex(), keys_only=True)

    assert _manifest(tmp_path) == [
        {"id": str(other.pk), "type": "file", "maintenanceKey": other.maintenance_wrapped_item_key}
    ]
    assert [path.name for path in tmp_path.iterdir()] == ["manifest.ndjson"]


# ============================================================================
# maintenance_import
# ============================================================================


def _exported_and_decrypted(tmp_path, *, invoice_failed=False):
    root, annexes, invoice = _tree()
    maintenance_escrow.export(tmp_path / "export")
    _decrypt(
        tmp_path / "export",
        tmp_path / "decrypted",
        plaintexts={str(invoice.pk): INVOICE},
        failed={str(invoice.pk)} if invoice_failed else (),
    )
    return root, annexes, invoice


@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_switches_a_tree_to_plaintext(analyse_file, tmp_path):
    """New object keys, pointers switched, keys cleared, old ciphertext kept, files scanned."""
    root, annexes, invoice = _exported_and_decrypted(tmp_path)
    old_key = invoice.file_key

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.switched == [str(root.pk)]
    for item in (root, annexes, invoice):
        item.refresh_from_db()
        assert item.is_encrypted is False
        assert item.encrypted_symmetric_key is None
    assert root.maintenance_wrapped_item_key is None
    assert not models.ItemEncryptionKeyWrap.objects.filter(item=root).exists()

    assert invoice.file_key != old_key
    assert invoice.file_key.endswith("/facture.pdf")
    assert default_storage.open(invoice.file_key).read() == INVOICE
    # The plaintext's, detected as upload_ended does, not the ciphertext's.
    assert invoice.mimetype == "application/pdf"
    assert invoice.size == len(INVOICE)
    # Kept for an investigation, an orphan for delete_orphan_objects.
    assert default_storage.open(old_key).read() == b"sealed invoice"
    analyse_file.assert_called_once_with(invoice.file_key, item_id=invoice.pk)


def test_maintenance_import_keeps_a_tree_edited_since_the_export(tmp_path):
    """The compare-and-swap on `updatedAt`: nothing changes, nothing is left uploaded."""
    root, annexes, invoice = _exported_and_decrypted(tmp_path)
    annexes.title = "Annexes renamed"
    annexes.save()

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped == {str(root.pk): "edited since the export"}
    invoice.refresh_from_db()
    assert invoice.is_encrypted is True
    assert _objects(invoice) == {invoice.file_key}


def test_maintenance_import_keeps_a_tree_whose_file_was_saved_in_place(tmp_path):
    """
    An editor saving in place (OnlyOffice) writes a new version of the object
    without touching the item: its ETag and version id give it away.
    """
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)
    client, bucket = _s3()
    client.put_object(Bucket=bucket, Key=invoice.file_key, Body=b"sealed invoice")

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped == {
        str(root.pk): f"the file of {invoice.pk} was overwritten since the export"
    }
    invoice.refresh_from_db()
    assert invoice.is_encrypted is True
    assert _objects(invoice) == {invoice.file_key}


def test_maintenance_import_keeps_a_tree_with_an_item_not_decrypted(tmp_path):
    """A tree goes whole or not at all: its escrow copy stays for the next export."""
    root, _annexes, _invoice = _exported_and_decrypted(tmp_path, invoice_failed=True)

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped == {str(root.pk): "1 item(s) could not be decrypted"}
    root.refresh_from_db()
    assert root.is_encrypted is True
    assert root.maintenance_wrapped_item_key == COPY_A


@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_goes_on_after_a_tree_fails(_analyse_file, tmp_path):
    """A failure inside one tree's transaction rolls it back, removes its uploads, and the
    next tree switches."""
    root, _annexes, invoice = _tree()
    second = _root(title="Second")
    note = _child(second, item_type=models.ItemTypeChoices.FILE, title="note.txt")
    _store(note, b"sealed note")
    maintenance_escrow.export(tmp_path / "export")
    _decrypt(
        tmp_path / "export",
        tmp_path / "decrypted",
        plaintexts={str(invoice.pk): INVOICE, str(note.pk): b"the note"},
    )
    real = maintenance_escrow.clear_subtree_encryption

    def failing_on_the_first(*, item, **kwargs):
        if item.pk == root.pk:
            raise RuntimeError("boom")
        return real(item=item, **kwargs)

    with mock.patch.object(
        maintenance_escrow, "clear_subtree_encryption", side_effect=failing_on_the_first
    ):
        summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped == {str(root.pk): "failed: RuntimeError: boom"}
    assert summary.switched == [str(second.pk)]
    root.refresh_from_db()
    assert root.is_encrypted is True
    assert _objects(invoice) == {invoice.file_key}
    note.refresh_from_db()
    assert note.is_encrypted is False


def test_maintenance_import_dry_run_changes_nothing(tmp_path):
    """--dry-run checks every tree and reports, without uploading or writing."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)

    output = StringIO()
    call_command("maintenance_import", str(tmp_path / "decrypted"), "--dry-run", stdout=output)

    assert "Would switch 1 tree(s) to plaintext." in output.getvalue()
    root.refresh_from_db()
    assert root.is_encrypted is True
    assert _objects(invoice) == {invoice.file_key}


def test_maintenance_import_dry_run_finds_a_file_missing_from_the_export(tmp_path):
    """The decrypted files are checked too, not only the database."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)
    (tmp_path / "decrypted" / "files" / str(invoice.pk)).unlink()

    summary = maintenance_escrow.import_export(tmp_path / "decrypted", dry_run=True)

    assert summary.skipped == {str(root.pk): f"files/{invoice.pk} is not in the export"}


def test_maintenance_import_refuses_a_file_outside_the_export(tmp_path):
    """A path out of the decrypted folder is never read."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)
    (tmp_path / "outside").write_bytes(b"not from the tool")
    manifest = tmp_path / "decrypted" / "manifest.ndjson"
    manifest.write_text(manifest.read_text().replace(f"files/{invoice.pk}", "../outside"))

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped == {str(root.pk): "../outside is not in the export"}


def test_maintenance_import_refuses_the_encrypted_export(tmp_path):
    """Given the export instead of the tool's output, it imports nothing at all."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)

    with pytest.raises(CommandError, match="this is the encrypted export"):
        call_command("maintenance_import", str(tmp_path / "export"))

    root.refresh_from_db()
    assert root.is_encrypted is True
    assert _objects(invoice) == {invoice.file_key}


def test_maintenance_import_refuses_a_folder_without_manifest(tmp_path):
    """The archive must be unzipped, or the folder the tool wrote given."""
    with pytest.raises(CommandError, match="No manifest.ndjson in"):
        call_command("maintenance_import", str(tmp_path))


@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_twice_is_harmless(_analyse_file, tmp_path):
    """Run again, a switched tree is reported as already in plaintext and left alone."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)
    maintenance_escrow.import_export(tmp_path / "decrypted")
    invoice.refresh_from_db()
    plaintext_key = invoice.file_key

    output = StringIO()
    call_command("maintenance_import", str(tmp_path / "decrypted"), stdout=output)

    assert "Switched 0 tree(s) to plaintext." in output.getvalue()
    assert f"Kept encrypted: {root.pk} (already in plaintext)" in output.getvalue()
    invoice.refresh_from_db()
    assert invoice.file_key == plaintext_key
    assert len(_objects(invoice)) == 2


@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_switches_an_outer_tree_before_an_inner_one(_analyse_file, tmp_path):
    """An inner root only goes back to plaintext once no encrypted tree contains it."""
    outer = _root(title="Outer")
    inner = _root(parent=outer, title="Inner", maintenance_key=_copy(ORGANIZATION_B))
    maintenance_escrow.export(tmp_path / "export")
    _decrypt(tmp_path / "export", tmp_path / "decrypted", plaintexts={})

    assert maintenance_escrow.import_export(tmp_path / "decrypted", dry_run=True).switched == [
        str(outer.pk),
        str(inner.pk),
    ]
    inner.refresh_from_db()
    assert inner.is_encrypted is True

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.switched == [str(outer.pk), str(inner.pk)]


def test_maintenance_import_keeps_an_inner_tree_until_its_outer_tree_switches(tmp_path):
    """Exported for its own key, an inner tree waits for the outer organization's import."""
    outer = _root(title="Outer")
    inner = _root(parent=outer, title="Inner", maintenance_key=_copy(ORGANIZATION_B))
    maintenance_escrow.export(tmp_path / "export", key_id=ORGANIZATION_B.hex())
    _decrypt(tmp_path / "export", tmp_path / "decrypted", plaintexts={})

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped[str(inner.pk)].startswith("inside another encrypted tree")


@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_a_file_moved_inside_its_tree(_analyse_file, tmp_path):
    """Moved within the tree, the file keeps its key and content: the tree switches."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)
    invoice.move(root)

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.switched == [str(root.pk)]
    invoice.refresh_from_db()
    assert invoice.is_encrypted is False
    assert str(invoice.path).rsplit(".", 1)[0] == str(root.path)


def test_maintenance_import_keeps_a_tree_a_file_moved_out_of(tmp_path):
    """Moved out, the file is no longer the tree's: the tree is not the one exported."""
    root, _annexes, invoice = _exported_and_decrypted(tmp_path)
    elsewhere = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, title="Elsewhere")
    invoice.move(elsewhere)

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.skipped == {str(root.pk): "edited since the export"}


@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_leaves_hard_deleted_descendants_alone(_analyse_file, tmp_path):
    """Purged, an item is in neither the export nor the import's tree, and is not switched."""
    root, annexes, invoice = _tree()
    gone = _child(annexes, item_type=models.ItemTypeChoices.FILE, title="gone.pdf")
    _store(gone, b"sealed")
    _hard_delete(gone)
    maintenance_escrow.export(tmp_path / "export")
    _decrypt(tmp_path / "export", tmp_path / "decrypted", plaintexts={str(invoice.pk): INVOICE})

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.switched == [str(root.pk)]
    gone.refresh_from_db()
    assert gone.is_encrypted is True


@pytest.mark.parametrize(
    "title, name",
    [("x" * 251 + ".pdf", re.compile(r"^x+\.pdf$")), ("..", "file"), (".", "file")],
)
@mock.patch("core.services.maintenance_escrow.malware_detection.analyse_file")
def test_maintenance_import_names_the_file_from_any_title(_analyse_file, title, name, tmp_path):
    """A title too long for `Item.filename` is cut, its extension kept; `.` and `..` are no
    names."""
    root = _root(item_type=models.ItemTypeChoices.FILE, title=title, filename="sealed")
    _store(root, b"sealed")
    maintenance_escrow.export(tmp_path / "export")
    _decrypt(tmp_path / "export", tmp_path / "decrypted", plaintexts={str(root.pk): INVOICE})

    summary = maintenance_escrow.import_export(tmp_path / "decrypted")

    assert summary.switched == [str(root.pk)]
    root.refresh_from_db()
    assert len(root.filename) <= 255
    stored_name = root.filename.split("/", 1)[1]
    assert name.match(stored_name) if isinstance(name, re.Pattern) else stored_name == name
    assert default_storage.open(root.file_key).read() == INVOICE


def test_maintenance_import_ignores_other_keys_folders(tmp_path):
    """Items set aside for another organization's key are not this import's business."""
    root, _annexes, _invoice = _exported_and_decrypted(tmp_path)
    other = tmp_path / "decrypted" / "other-keys" / "1234"
    other.mkdir(parents=True)
    (other / "manifest.ndjson").write_text(json.dumps({"id": "x", "maintenanceKey": "AAAA"}) + "\n")

    summary = maintenance_escrow.import_export(tmp_path / "decrypted", dry_run=True)

    assert summary.switched == [str(root.pk)]


# ============================================================================
# maintenance_rotate
# ============================================================================


def _write_manifest(folder, lines):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.ndjson").write_text("".join(json.dumps(line) + "\n" for line in lines))


def _rotated(export_dir, rotated_dir):
    """What the tool's rotation hands back: each copy re-wrapped, the exported one beside it."""
    new_copies = {}
    lines = []
    for line in _manifest(export_dir):
        line["previousMaintenanceKey"] = line.pop("maintenanceKey")
        line["maintenanceKey"] = new_copies[line["id"]] = _copy(ORGANIZATION_B)
        lines.append(line)
    _write_manifest(rotated_dir, lines)
    return new_copies


def _two_roots_rotated(tmp_path):
    first = _root(title="First")
    second = _root(title="Second", item_type=models.ItemTypeChoices.FILE, filename="sealed")
    maintenance_escrow.export(tmp_path / "export", key_id=ORGANIZATION_A.hex(), keys_only=True)
    new_copies = _rotated(tmp_path / "export", tmp_path / "rotated")
    return first, second, new_copies


def _copy_of(item):
    return models.Item.objects.get(pk=item.pk).maintenance_wrapped_item_key


def test_maintenance_rotate_replaces_the_copies(tmp_path):
    """Every root gets its new copy, without being taken as edited."""
    first, second, new_copies = _two_roots_rotated(tmp_path)
    updated_at = {item.pk: item.updated_at for item in (first, second)}

    output = StringIO()
    call_command("maintenance_rotate", str(tmp_path / "rotated"), stdout=output)

    assert "Rotated the copies of 2 encryption root(s)." in output.getvalue()
    assert "Not rotated" not in output.getvalue()
    for item in (first, second):
        item.refresh_from_db()
        assert item.maintenance_wrapped_item_key == new_copies[str(item.pk)]
        assert item.updated_at == updated_at[item.pk]


def test_maintenance_rotate_keeps_a_copy_changed_since_the_export(tmp_path):
    """A root whose copy changed meanwhile keeps it; a root gone is named too."""
    first, second, new_copies = _two_roots_rotated(tmp_path)
    models.Item.objects.filter(pk=first.pk).update(
        maintenance_wrapped_item_key=_copy(ORGANIZATION_B)
    )
    changed = _copy_of(first)
    third = _root(title="Third")
    lines = _manifest(tmp_path / "rotated") + [
        {
            "id": str(uuid4()),
            "type": "folder",
            "previousMaintenanceKey": COPY_A,
            "maintenanceKey": _copy(ORGANIZATION_B),
        }
    ]
    _write_manifest(tmp_path / "rotated", lines)

    summary = maintenance_escrow.rotate(tmp_path / "rotated")

    assert summary.rotated == [str(second.pk)]
    assert summary.skipped == {
        str(first.pk): "its copy changed since the export",
        lines[-1]["id"]: "no longer exists",
    }
    assert _copy_of(first) == changed
    assert _copy_of(second) == new_copies[str(second.pk)]
    assert _copy_of(third) == COPY_A


def test_maintenance_rotate_skips_what_the_tool_could_not_re_wrap(tmp_path):
    """A line with the tool's error, or a new copy that is not one, leaves the old copy."""
    first, second, _new_copies = _two_roots_rotated(tmp_path)
    lines = _manifest(tmp_path / "rotated")
    by_id = {line["id"]: line for line in lines}
    del by_id[str(first.pk)]["maintenanceKey"]
    by_id[str(first.pk)]["error"] = "WRONG_SECRET_KEY: decryption failed"
    by_id[str(second.pk)]["maintenanceKey"] = "not base64!"
    _write_manifest(tmp_path / "rotated", lines)

    output = StringIO()
    call_command("maintenance_rotate", str(tmp_path / "rotated"), stdout=output)

    assert "Rotated the copies of 0 encryption root(s)." in output.getvalue()
    assert (
        f"Not rotated: {first.pk} (the tool could not re-wrap it: "
        "WRONG_SECRET_KEY: decryption failed)"
    ) in output.getvalue()
    assert (
        f"Not rotated: {second.pk} (the new copy is not a maintenance escrow copy)"
    ) in output.getvalue()
    assert _copy_of(first) == COPY_A
    assert _copy_of(second) == COPY_A


def test_maintenance_rotate_dry_run_changes_nothing(tmp_path):
    """A dry run reports what a real run would rotate and skip."""
    first, second, _new_copies = _two_roots_rotated(tmp_path)
    models.Item.objects.filter(pk=first.pk).update(maintenance_wrapped_item_key=None)

    output = StringIO()
    call_command("maintenance_rotate", str(tmp_path / "rotated"), "--dry-run", stdout=output)

    assert "Would rotate the copies of 1 encryption root(s)." in output.getvalue()
    assert f"Not rotated: {first.pk} (its copy changed since the export)" in output.getvalue()
    assert _copy_of(first) is None
    assert _copy_of(second) == COPY_A


def test_maintenance_rotate_is_all_or_nothing(tmp_path):
    """A failure on the second root undoes the first: the run is simply started again."""
    first, second, _new_copies = _two_roots_rotated(tmp_path)
    real_update = QuerySet.update
    calls = []

    def update(queryset, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("database gone")
        return real_update(queryset, **kwargs)

    with (
        mock.patch.object(QuerySet, "update", autospec=True, side_effect=update),
        pytest.raises(RuntimeError),
    ):
        maintenance_escrow.rotate(tmp_path / "rotated")

    assert len(calls) == 2
    assert _copy_of(first) == COPY_A
    assert _copy_of(second) == COPY_A
