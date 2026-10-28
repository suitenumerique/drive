"""
Tests for the rotation of the maintenance copies to a new maintenance key, end to
end through the commands: `maintenance_export --keys-only --fingerprint`, the
maintenance tool's re-wrap (simulated), then `maintenance_rotate`. Only the
database is involved: the rotation writes one column of the encryption roots.
"""

import base64
import json
import os
from io import StringIO
from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db

OLD_KEY = bytes(range(16))
NEW_KEY = bytes(range(32, 48))
OTHER_ORGANIZATION = bytes(range(16, 32))


def _fingerprint(key_id):
    """The 40 digits the tool shows for a key id: the scheme digit, then the id as a number."""
    return "1" + str(int.from_bytes(key_id, "big")).zfill(39)


def _copy(key_id=OLD_KEY):
    """A maintenance copy as the vault writes it: version byte, key id, then the wrap."""
    return base64.b64encode(bytes([1]) + key_id + os.urandom(1120)).decode()


def _wrap():
    """A key wrapped by its parent's, as the vault writes it: nonce, key, tag."""
    return base64.b64encode(os.urandom(24 + 32 + 16)).decode()


def _root(*, key_id=OLD_KEY, item_type=models.ItemTypeChoices.FOLDER, **kwargs):
    if item_type == models.ItemTypeChoices.FILE:
        kwargs.setdefault("filename", "sealed")
    return factories.ItemFactory(
        type=item_type,
        is_encrypted=True,
        encrypted_symmetric_key=None,
        maintenance_wrapped_item_key=_copy(key_id),
        **kwargs,
    )


def _child(parent):
    return factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        is_encrypted=True,
        encrypted_symmetric_key=_wrap(),
    )


def _run(command, *args):
    """Run a command, returning what it printed, line by line."""
    output = StringIO()
    call_command(command, *args, stdout=output)
    return output.getvalue().splitlines()


def _manifest(folder):
    return [json.loads(line) for line in (folder / "manifest.ndjson").read_text().splitlines()]


def _write_manifest(folder, lines):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.ndjson").write_text("".join(json.dumps(line) + "\n" for line in lines))


def _export(folder, key_id=OLD_KEY):
    """The keys-only export of one key's roots, through the command an operator runs."""
    _run(
        "maintenance_export",
        "--output",
        str(folder),
        "--keys-only",
        "--fingerprint",
        _fingerprint(key_id),
    )


def _rotate_with_the_tool(export_dir, rotated_dir):
    """
    What the tool's Rotate tab hands back for an export: each line kept, the new
    copy in `maintenanceKey`, the exported one in `previousMaintenanceKey`.
    """
    lines = []
    for line in _manifest(export_dir):
        previous = line.pop("maintenanceKey")
        lines.append({**line, "maintenanceKey": _copy(NEW_KEY), "previousMaintenanceKey": previous})
    _write_manifest(rotated_dir, lines)
    return {line["id"]: line["maintenanceKey"] for line in lines}


def _stored(item):
    return models.Item.objects.get(pk=item.pk).maintenance_wrapped_item_key


def _rotated_line(item, **fields):
    """A rotated line for one root, its new copy for the new key."""
    return {
        "id": str(item.pk),
        "type": item.type,
        "maintenanceKey": _copy(NEW_KEY),
        "previousMaintenanceKey": item.maintenance_wrapped_item_key,
        **fields,
    }


def test_maintenance_rotate_round_trip_through_the_commands(tmp_path):
    """
    The roots of the old key get their new copy, nested root included; another
    organization's root and every descendant's wrapped key stay as they are, and
    nothing counts as edited.
    """
    outer = _root(title="Outer")
    below = _child(outer)
    inner = _root(parent=below, title="Inner")
    file_root = _root(item_type=models.ItemTypeChoices.FILE, title="sealed.pdf")
    elsewhere = _root(key_id=OTHER_ORGANIZATION, title="Elsewhere")
    elsewhere_copy = _stored(elsewhere)
    below_wrap = below.encrypted_symmetric_key
    updated_at = {item.pk: item.updated_at for item in (outer, inner, file_root)}

    _export(tmp_path / "export")
    assert {line["id"] for line in _manifest(tmp_path / "export")} == {
        str(outer.pk),
        str(inner.pk),
        str(file_root.pk),
    }
    new_copies = _rotate_with_the_tool(tmp_path / "export", tmp_path / "rotated")

    assert _run("maintenance_rotate", str(tmp_path / "rotated")) == [
        "Rotated the copies of 3 encryption root(s)."
    ]

    for item in (outer, inner, file_root):
        item.refresh_from_db()
        assert item.maintenance_wrapped_item_key == new_copies[str(item.pk)]
        assert item.updated_at == updated_at[item.pk]
    assert _stored(elsewhere) == elsewhere_copy
    below.refresh_from_db()
    assert below.encrypted_symmetric_key == below_wrap
    assert below.maintenance_wrapped_item_key is None

    # The new key now finds the rotated roots, the old one none.
    _export(tmp_path / "old-key-after")
    _export(tmp_path / "new-key-after", key_id=NEW_KEY)
    assert _manifest(tmp_path / "old-key-after") == []
    assert {line["id"] for line in _manifest(tmp_path / "new-key-after")} == set(new_copies)


def test_maintenance_rotate_twice_is_harmless(tmp_path):
    """
    A rerun of the same file finds the new copies in place of the previous ones:
    it skips every root and keeps them.
    """
    first = _root()
    second = _root()
    _export(tmp_path / "export")
    new_copies = _rotate_with_the_tool(tmp_path / "export", tmp_path / "rotated")
    _run("maintenance_rotate", str(tmp_path / "rotated"))

    output = _run("maintenance_rotate", str(tmp_path / "rotated"))

    assert output[0] == "Rotated the copies of 0 encryption root(s)."
    assert sorted(output[1:]) == sorted(
        f"Not rotated: {item.pk} (its copy changed since the export)" for item in (first, second)
    )
    assert {str(item.pk): _stored(item) for item in (first, second)} == new_copies


def test_maintenance_rotate_keeps_a_root_switched_to_plaintext_since_the_export(tmp_path):
    """A root put back in plaintext lost its copy: the rotation must not give it one again."""
    switched = _root()
    kept = _root()
    _export(tmp_path / "export")
    new_copies = _rotate_with_the_tool(tmp_path / "export", tmp_path / "rotated")
    models.Item.objects.filter(pk=switched.pk).update(
        is_encrypted=False, maintenance_wrapped_item_key=None
    )

    output = _run("maintenance_rotate", str(tmp_path / "rotated"))

    assert output == [
        "Rotated the copies of 1 encryption root(s).",
        f"Not rotated: {switched.pk} (its copy changed since the export)",
    ]
    assert _stored(switched) is None
    assert _stored(kept) == new_copies[str(kept.pk)]


def test_maintenance_rotate_refuses_the_export_itself(tmp_path):
    """The keys-only export given before the tool re-wrapped it: every root skipped, named."""
    root = _root()
    previous = _stored(root)
    _export(tmp_path / "export")

    output = _run("maintenance_rotate", str(tmp_path / "export"))

    assert output == [
        "Rotated the copies of 0 encryption root(s).",
        f"Not rotated: {root.pk} (no previousMaintenanceKey: not the output of a rotation)",
    ]
    assert _stored(root) == previous


def test_maintenance_rotate_skips_a_root_of_another_key(tmp_path):
    """
    The tool cannot open a copy made for another key: it hands the line back with
    its error and no new copy, and the root keeps its copy.
    """
    elsewhere = _root(key_id=OTHER_ORGANIZATION)
    previous = _stored(elsewhere)
    line = _rotated_line(
        elsewhere, error="OTHER_KEY: escrowed for another maintenance key (1 0000 ...)"
    )
    del line["maintenanceKey"]
    _write_manifest(tmp_path, [line])

    output = _run("maintenance_rotate", str(tmp_path))

    assert output == [
        "Rotated the copies of 0 encryption root(s).",
        f"Not rotated: {elsewhere.pk} (the tool could not re-wrap it: "
        "OTHER_KEY: escrowed for another maintenance key (1 0000 ...))",
    ]
    assert _stored(elsewhere) == previous


@pytest.mark.parametrize(
    "new_copy",
    [
        None,
        42,
        "not base64!",
        # Base64, but not a copy: wrong version byte, or nothing after the header.
        base64.b64encode(bytes([2]) + NEW_KEY + bytes(1120)).decode(),
        base64.b64encode(bytes([1]) + NEW_KEY).decode(),
    ],
    ids=["missing", "not text", "not base64", "wrong version", "header only"],
)
def test_maintenance_rotate_skips_a_new_copy_that_is_not_one(new_copy, tmp_path):
    """Only a well-formed copy is written, checked as the maintenance-key endpoint checks it."""
    root = _root()
    previous = _stored(root)
    line = _rotated_line(root, maintenanceKey=new_copy)
    if new_copy is None:
        del line["maintenanceKey"]
    _write_manifest(tmp_path, [line])

    output = _run("maintenance_rotate", str(tmp_path))

    assert output == [
        "Rotated the copies of 0 encryption root(s).",
        f"Not rotated: {root.pk} (the new copy is not a maintenance escrow copy)",
    ]
    assert _stored(root) == previous


def test_maintenance_rotate_skips_malformed_lines_and_rotates_the_others(tmp_path):
    """A line without an item id, or with a previous copy that is not text, is named and skipped."""
    root = _root()
    no_previous = _root()
    lines = [
        {"type": "folder", "maintenanceKey": _copy(NEW_KEY), "previousMaintenanceKey": _copy()},
        {"id": "../etc", "maintenanceKey": _copy(NEW_KEY), "previousMaintenanceKey": _copy()},
        _rotated_line(no_previous, previousMaintenanceKey=None),
        _rotated_line(root),
    ]
    _write_manifest(tmp_path, lines)
    previous = _stored(no_previous)

    output = _run("maintenance_rotate", str(tmp_path))

    assert output == [
        "Rotated the copies of 1 encryption root(s).",
        "Not rotated: None (not an item id)",
        "Not rotated: ../etc (not an item id)",
        f"Not rotated: {no_previous.pk} (no previousMaintenanceKey: not the output of a rotation)",
    ]
    assert _stored(root) == lines[-1]["maintenanceKey"]
    assert _stored(no_previous) == previous


def test_maintenance_rotate_ignores_blank_lines(tmp_path):
    """An empty line (a trailing newline too many) is no root."""
    root = _root()
    line = _rotated_line(root)
    (tmp_path / "manifest.ndjson").write_text("\n" + json.dumps(line) + "\n\n  \n")

    assert _run("maintenance_rotate", str(tmp_path)) == [
        "Rotated the copies of 1 encryption root(s)."
    ]
    assert _stored(root) == line["maintenanceKey"]


def test_maintenance_rotate_refuses_a_file_that_is_not_ndjson(tmp_path):
    """The whole file is read before any write: a broken line writes nothing at all."""
    root = _root()
    previous = _stored(root)
    (tmp_path / "manifest.ndjson").write_text(json.dumps(_rotated_line(root)) + "\n{not json\n")

    with pytest.raises(CommandError, match="Line 2 of manifest.ndjson is not JSON"):
        _run("maintenance_rotate", str(tmp_path))

    assert _stored(root) == previous


def test_maintenance_rotate_refuses_a_folder_without_manifest(tmp_path):
    """The archive must be unzipped, or the folder the tool wrote given."""
    with pytest.raises(CommandError, match="No manifest.ndjson in"):
        _run("maintenance_rotate", str(tmp_path))


def test_maintenance_rotate_dry_run_reports_without_writing(tmp_path):
    """--dry-run tells the roots it would rotate and those it would skip, and writes nothing."""
    rotatable = _root()
    changed = _root()
    gone = _root()
    lines = [_rotated_line(item) for item in (rotatable, changed, gone)]
    models.Item.objects.filter(pk=changed.pk).update(maintenance_wrapped_item_key=_copy())
    changed_copy = _stored(changed)
    models.Item.objects.filter(pk=gone.pk).delete()
    lines.append(
        {
            "id": str(uuid4()),
            "maintenanceKey": _copy(NEW_KEY),
            "previousMaintenanceKey": _copy(),
        }
    )
    _write_manifest(tmp_path, lines)

    output = _run("maintenance_rotate", str(tmp_path), "--dry-run")

    assert output == [
        "Would rotate the copies of 1 encryption root(s).",
        f"Not rotated: {changed.pk} (its copy changed since the export)",
        f"Not rotated: {gone.pk} (no longer exists)",
        f"Not rotated: {lines[-1]['id']} (no longer exists)",
    ]
    assert _stored(rotatable) == rotatable.maintenance_wrapped_item_key
    assert _stored(changed) == changed_copy

    # The same file for real does what the dry run said.
    assert _run("maintenance_rotate", str(tmp_path))[0] == (
        "Rotated the copies of 1 encryption root(s)."
    )
    assert _stored(rotatable) == lines[0]["maintenanceKey"]
