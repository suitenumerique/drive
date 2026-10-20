"""
Batch recovery through the maintenance escrow: the export the LaSuite maintenance
tool decrypts, and the import of what it hands back.

An encryption root carries `maintenance_wrapped_item_key`, its key wrapped for its
owner's organization's maintenance key. Every item below it carries
`encrypted_symmetric_key`, its own key wrapped by its parent's (the vault's
`wrapped-key` label, which the tool unwraps), and a file's content sits in object
storage at its `file_key`, encrypted with the file's key. That maps one to one onto
the tool's generic export: the root with `maintenanceKey`, every descendant with
`parent` + `wrappedKey`, files with `file`, folders carrying a key only.

The import puts a tree back in plaintext the way the remove-encryption endpoint
does, one tree per transaction: the decrypted files are uploaded under NEW object
keys first, the pointers switch in the transaction, and the new objects are deleted
after a rollback. The old encrypted objects are kept after the commit, for an
investigation, until `delete_orphan_objects` deletes them. A tree changed since the
export (an item edited, added or removed, a file overwritten), or with any item the
tool could not decrypt, is left encrypted, to be exported again.

When an organization replaces its maintenance key, its copies are re-wrapped for
the new one: the keys-only export hands the tool the copies alone, the tool re-wraps
them offline with the old phrase, and the rotation writes the new copies back.
"""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import BooleanField
from django.db.models.expressions import RawSQL
from django.utils.dateparse import parse_datetime

from botocore.exceptions import ClientError
from lasuite.malware_detection import malware_detection
from rest_framework.exceptions import ValidationError

from core import models
from core.api.serializers import validate_maintenance_key
from core.api.utils import detect_mimetype
from core.api.viewsets import clear_subtree_encryption, compute_removal_scope

logger = logging.getLogger(__name__)

MANIFEST_FILE = "manifest.ndjson"
FILES_FOLDER = "files"
CHUNK_SIZE = 8 * 1024 * 1024
KEY_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
FINGERPRINT_PATTERN = re.compile(r"^1[0-9]{39}$")
UNSAFE_FILENAME = re.compile(r"[/\\\x00]")
FILENAME_MAX_LENGTH = models.Item._meta.get_field("filename").max_length  # noqa: SLF001
# Longer than this, what follows the last dot is part of the name, not an extension.
EXTENSION_MAX_LENGTH = 16
# What `upload_ended` reads of a file to detect its type.
MIMETYPE_SAMPLE_SIZE = 2048
MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}
# Pass-through fields of a file's line: the stored version its ciphertext was read
# from. An editor saving in place (OnlyOffice) overwrites the object without
# touching the item, so `updatedAt` alone would not see it.
OBJECT_IDENTITY_FIELDS = ("objectEtag", "objectVersionId")


def key_id_from_fingerprint(fingerprint):
    """
    The key id, in hexadecimal, of the maintenance key with this fingerprint: the 40
    digits the maintenance tool and the encryption server's startup log show, spaces
    allowed. The id is the fingerprint without its scheme digit, read as a number.
    """
    digits = "".join(fingerprint.split())

    if not FINGERPRINT_PATTERN.match(digits) or int(digits[1:]) >= 2**128:
        raise ValueError(
            "A maintenance key fingerprint is 40 digits starting with 1, as the "
            "maintenance tool and the encryption server's startup log show it."
        )

    return int(digits[1:]).to_bytes(16, "big").hex()


def encryption_roots(key_id=None):
    """
    Encryption roots, outer before inner. `key_id` (32 hex characters, from the key's
    fingerprint by `key_id_from_fingerprint`) keeps the roots whose escrow copy names
    that key: bytes 2 to 17 of the copy, matched in SQL.
    """
    roots = models.Item.objects.filter(
        is_encrypted=True,
        encrypted_symmetric_key__isnull=True,
        hard_deleted_at__isnull=True,
    ).exclude(type=models.ItemTypeChoices.RESTRICTION)

    if key_id is not None:
        if not KEY_ID_PATTERN.match(key_id):
            raise ValueError("The key id is 32 hexadecimal characters.")
        roots = roots.filter(
            RawSQL(
                "substring(decode(maintenance_wrapped_item_key, 'base64') from 2 for 16) "
                "= decode(%s, 'hex')",
                [key_id],
                output_field=BooleanField(),
            ),
            maintenance_wrapped_item_key__isnull=False,
        )

    return sorted(roots, key=lambda item: len(item.path))


def _scope(root):
    """The descendants that go back to plaintext with `root`, those not purged."""
    return compute_removal_scope(root).filter(hard_deleted_at__isnull=True)


def _tree(root):
    """The root and the items that go back to plaintext with it, parents before children."""
    descendants = _scope(root).exclude(type=models.ItemTypeChoices.RESTRICTION)

    return [root, *sorted(descendants, key=lambda item: len(item.path))]


def _s3():
    return default_storage.connection.meta.client, default_storage.bucket_name


def _is_missing(error):
    return error.response.get("Error", {}).get("Code") in MISSING_OBJECT_CODES


def _identity(response):
    """The stored version a get or head response describes (no version id when the bucket is not versioned)."""
    identity = {"objectEtag": response["ETag"]}
    if response.get("VersionId"):
        identity["objectVersionId"] = response["VersionId"]
    return identity


def _manifest_lines(root):
    """Each item's manifest line, with the object key of its content for a file."""
    by_path = {}

    for item in _tree(root):
        by_path[str(item.path)] = item
        line = {
            "id": str(item.pk),
            "type": item.type,
            "title": item.title,
            "updatedAt": item.updated_at.isoformat(),
        }

        if item is root:
            line["maintenanceKey"] = item.maintenance_wrapped_item_key
        else:
            line["parent"] = str(by_path[str(item.path[:-1])].pk)
            if item.encrypted_symmetric_key:
                line["wrappedKey"] = item.encrypted_symmetric_key

        object_key = None

        if item.type == models.ItemTypeChoices.FILE and item.filename:
            # Named after the item id, not its object key, which ends with the file
            # name: no name of the user's in the export's paths, and no character a
            # file system or an archive could refuse. The import uploads under new
            # keys anyway.
            line["file"] = f"{FILES_FOLDER}/{item.pk}"
            object_key = item.file_key

        yield line, object_key


@dataclass
class ExportSummary:
    """What an export wrote, and the trees it could not include."""

    trees: int = 0
    items: int = 0
    files: int = 0
    missing_objects: list = field(default_factory=list)
    without_copy: int = 0


def _key_line(root):
    """A keys-only export's line: the root and its copy, nothing below it."""
    yield (
        {
            "id": str(root.pk),
            "type": root.type,
            "maintenanceKey": root.maintenance_wrapped_item_key,
        },
        None,
    )


def export(output_dir, key_id=None, keys_only=False):
    """
    Write the export of every encryption root (or those of one key) into
    `output_dir`. `keys_only`: one line per root with its copy, nothing below it and
    no file, what the tool re-wraps for a new maintenance key.
    """
    output = Path(output_dir)
    # Files of an earlier export would be taken for this one's by whoever reads it.
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"{output} is not empty: export into a new folder.")
    output.mkdir(parents=True, exist_ok=True)
    summary = ExportSummary()

    with (output / MANIFEST_FILE).open("w", encoding="utf-8") as manifest:
        for root in encryption_roots(key_id):
            # Without a copy no key can open the tree: created before the escrow was
            # enabled or before its owner's domain was covered, and not backfilled.
            if not root.maintenance_wrapped_item_key:
                summary.without_copy += 1
                continue

            summary.trees += 1
            lines = _key_line(root) if keys_only else _manifest_lines(root)

            for line, object_key in lines:
                if object_key is not None:
                    identity = _copy_object(object_key, output / line["file"])
                    if identity is None:
                        # Without its identity the import keeps the tree encrypted.
                        summary.missing_objects.append(object_key)
                    else:
                        line.update(identity)
                        summary.files += 1

                manifest.write(json.dumps(line, ensure_ascii=False) + "\n")
                summary.items += 1

    return summary


def _copy_object(key, destination):
    """
    Stream one object out of the storage, chunk by chunk (a file can weigh
    gigabytes), and return the identity of the version read, None when it is missing.
    """
    client, bucket = _s3()

    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if _is_missing(error):
            return None
        raise

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as target:
        for chunk in response["Body"].iter_chunks(CHUNK_SIZE):
            target.write(chunk)

    return _identity(response)


@dataclass
class ImportSummary:
    """Trees switched to plaintext, and why the others were not."""

    switched: list = field(default_factory=list)
    skipped: dict = field(default_factory=dict)


@dataclass
class _Upload:
    filename: str
    mimetype: str
    size: int


class _Skip(Exception):
    pass


class ManifestError(Exception):
    """A folder that is not one the maintenance tool wrote: refused before anything."""


def _read_manifest(export_dir):
    path = Path(export_dir) / MANIFEST_FILE

    # An archive not unzipped, or the wrong folder given.
    if not path.is_file():
        raise ManifestError(f"No {MANIFEST_FILE} in {export_dir}.")

    lines = []

    with path.open(encoding="utf-8") as manifest:
        for number, line in enumerate(manifest, start=1):
            if not line.strip():
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ManifestError(
                    f"Line {number} of {MANIFEST_FILE} is not JSON ({error.msg})."
                ) from error

    return lines


def _trees_of(lines):
    """The decrypted manifest's trees: each root (a line without `parent`) and all below it."""
    children = {}

    for line in lines:
        if "parent" in line:
            children.setdefault(line["parent"], []).append(line)

    def collect(line):
        yield line
        for child in children.get(line["id"], []):
            yield from collect(child)

    return {line["id"]: list(collect(line)) for line in lines if "parent" not in line}


def _source(export_dir, line):
    """The decrypted file of a line, never a path outside the export."""
    folder = Path(export_dir).resolve()
    source = (folder / line["file"]).resolve()

    if not source.is_relative_to(folder) or not source.is_file():
        raise _Skip(f"{line['file']} is not in the export")

    return source


def _check_root(root, plaintext=frozenset()):
    """
    Why `root` cannot switch now, if it cannot. `plaintext`: ids of encrypted items
    to count as plaintext already (a dry run's outer trees, which a real run would
    have switched first).
    """
    if root is None:
        raise _Skip("no longer exists")
    if not root.is_encrypted:
        raise _Skip("already in plaintext")
    if root.encrypted_symmetric_key is not None:
        raise _Skip("no longer an encryption root")
    if root.ancestors().filter(is_encrypted=True).exclude(pk__in=plaintext).exists():
        raise _Skip(
            "inside another encrypted tree: import the outer tree first (when it is "
            "another organization's, after that organization's import)"
        )


def _check(export_dir, root_id, lines, plaintext=frozenset()):
    """The live root, or the reason this tree must stay encrypted for now."""
    failed = [line["id"] for line in lines if "error" in line]
    if failed:
        raise _Skip(f"{len(failed)} item(s) could not be decrypted")

    root = models.Item.objects.filter(pk=root_id).first()
    _check_root(root, plaintext)

    for line in lines:
        if "file" in line:
            _source(export_dir, line)

    _compare(_tree(root), lines)

    return root


def _compare(live, lines):
    """
    The tree as exported: the same items, none edited since (`updatedAt`), every
    file still the version that was exported (its ETag and version id).
    """
    exported = {line["id"]: line for line in lines}

    if {str(item.pk): item.updated_at for item in live} != {
        item_id: parse_datetime(line["updatedAt"]) for item_id, line in exported.items()
    }:
        raise _Skip("edited since the export")

    client, bucket = _s3()

    for item in live:
        if item.type != models.ItemTypeChoices.FILE or not item.filename:
            continue

        line = exported[str(item.pk)]
        identity = {name: line[name] for name in OBJECT_IDENTITY_FIELDS if name in line}
        if not identity:
            raise _Skip(f"the file of {item.pk} was missing from the storage at the export")

        try:
            head = client.head_object(Bucket=bucket, Key=item.file_key)
        except ClientError as error:
            if _is_missing(error):
                raise _Skip(f"the file of {item.pk} is missing from the storage") from error
            raise

        if _identity(head) != identity:
            raise _Skip(f"the file of {item.pk} was overwritten since the export")


def _staged_filename(title):
    """
    A new folder then the item's title, as the encryption job names its uploads (a
    new key, and the name a download gets), cut to fit `Item.filename` with its
    extension kept.
    """
    folder = str(uuid.uuid4())
    name = UNSAFE_FILENAME.sub("_", title or "")
    # A storage normalises `.` and `..` away (or refuses them): no name of the item's.
    if name in ("", ".", ".."):
        name = "file"

    room = FILENAME_MAX_LENGTH - len(folder) - 1
    if len(name) > room:
        stem, extension = os.path.splitext(name)
        if len(extension) > EXTENSION_MAX_LENGTH:
            stem, extension = name, ""
        name = stem[: room - len(extension)] + extension

    return f"{folder}/{name}"


def _upload(export_dir, lines):
    """The decrypted files under new object keys, for each file item id."""
    uploaded = {}

    try:
        for line in lines:
            if "file" not in line:
                continue

            source = _source(export_dir, line)
            prefix = f"item/{line['id']}/"

            with source.open("rb") as content:
                sample = content.read(MIMETYPE_SAMPLE_SIZE)
                content.seek(0)
                # The storage may change the name it was given: the key is the one it returns.
                key = default_storage.save(
                    prefix + _staged_filename(line.get("title")), File(content)
                )

            filename = key.removeprefix(prefix)
            uploaded[line["id"]] = _Upload(
                filename=filename,
                mimetype=detect_mimetype(sample, filename=filename),
                size=source.stat().st_size,
            )
    except BaseException:
        _delete(f"item/{item_id}/{upload.filename}" for item_id, upload in uploaded.items())
        raise

    return uploaded


def _delete(keys):
    for key in keys:
        try:
            default_storage.delete(key)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            logger.warning("Failed to delete object %s", key)


def _switch(export_dir, root_id, lines):
    """Upload a checked tree's plaintext and switch the tree to it, in one transaction."""
    uploaded = _upload(export_dir, lines)

    try:
        with transaction.atomic():
            root = models.Item.objects.select_for_update().filter(pk=root_id).first()
            # Checked again under the lock: the tree may have changed since the first check.
            _check_root(root)
            list(
                models.Item.objects.select_for_update().filter(
                    pk__in=[item.pk for item in _tree(root)]
                )
            )
            _compare(_tree(root), lines)
            # The old encrypted objects stay, for an investigation should something
            # go wrong: no item points to them any more, so `delete_orphan_objects`
            # deletes them once the batch is checked.
            _old_keys, files_to_scan = clear_subtree_encryption(
                item=root,
                file_key_mapping={item_id: upload.filename for item_id, upload in uploaded.items()},
                effective_descendants=_scope(root),
                # Uploaded encrypted, a file carries the ciphertext's type and size.
                file_metadata={
                    item_id: {"mimetype": upload.mimetype, "size": upload.size}
                    for item_id, upload in uploaded.items()
                },
            )
    except BaseException:
        _delete(f"item/{item_id}/{upload.filename}" for item_id, upload in uploaded.items())
        raise

    for file_key, item_id in files_to_scan:
        try:
            malware_detection.analyse_file(file_key, item_id=item_id)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to send %s to malware detection", file_key)


def import_export(export_dir, dry_run=False):
    """Switch each tree of a DECRYPTED export back to plaintext, those it can."""
    summary = ImportSummary()
    lines = _read_manifest(export_dir)
    # The tool drops every key from what it decrypts: a line still carrying one is
    # the encrypted export (or a rotation's output), whose files are ciphertext that
    # would be written as plaintext.
    still_encrypted = [
        line.get("id") for line in lines if "maintenanceKey" in line or "wrappedKey" in line
    ]

    if still_encrypted:
        raise ManifestError(
            f"{len(still_encrypted)} lines of {MANIFEST_FILE} still carry a key "
            f"(maintenanceKey or wrappedKey), the first for {still_encrypted[0]}: this is "
            "the encrypted export, not the decrypted copy the maintenance tool saves. "
            "Nothing was imported."
        )

    trees = _trees_of(lines)
    live_roots = {str(item.pk): item for item in models.Item.objects.filter(pk__in=trees.keys())}
    # Outer trees before inner ones: an inner root only switches once no encrypted
    # tree contains it (as the remove-encryption endpoint requires).
    order = sorted(
        trees, key=lambda root_id: len(live_roots[root_id].path) if root_id in live_roots else 0
    )
    # A dry run switches nothing: the items of the trees it would switch count as
    # plaintext for the trees nested in them.
    would_switch = set()

    for root_id in order:
        lines = trees[root_id]

        try:
            _check(export_dir, root_id, lines, would_switch)
            if dry_run:
                would_switch.update(line["id"] for line in lines)
            else:
                _switch(export_dir, root_id, lines)
        except _Skip as reason:
            summary.skipped[root_id] = str(reason)
            continue
        except Exception as error:  # pylint: disable=broad-exception-caught
            # A storage or database error on one tree leaves the others to switch.
            logger.exception("Failed to switch the tree %s to plaintext", root_id)
            summary.skipped[root_id] = f"failed: {type(error).__name__}: {error}"
            continue

        summary.switched.append(root_id)

    return summary


@dataclass
class RotateSummary:
    """Roots whose copy was re-wrapped for the new maintenance key, and why the others were not."""

    rotated: list = field(default_factory=list)
    skipped: dict = field(default_factory=dict)


def _new_copy(line):
    """The checked new copy of a re-wrapped line, or the reason it is not one."""
    if "error" in line:
        raise _Skip(f"the tool could not re-wrap it: {line['error']}")
    try:
        uuid.UUID(str(line.get("id")))
    except ValueError as error:
        raise _Skip("not an item id") from error
    if not isinstance(line.get("previousMaintenanceKey"), str):
        raise _Skip("no previousMaintenanceKey: not the output of a rotation")

    new_copy = line.get("maintenanceKey")
    # Checked as the maintenance-key endpoint checks it: the shape only.
    try:
        if isinstance(new_copy, str) and validate_maintenance_key(new_copy):
            return new_copy
    except ValidationError:
        pass
    raise _Skip("the new copy is not a maintenance escrow copy")


def rotate(rotated_dir, dry_run=False):
    """
    Write back the copies the tool re-wrapped for a new maintenance key, each root
    only while it still carries the copy that was exported.
    """
    summary = RotateSummary()
    checked = []

    for line in _read_manifest(rotated_dir):
        try:
            # Checked first: it is what makes `id` and `previousMaintenanceKey` safe to read.
            new_copy = _new_copy(line)
            checked.append((line["id"], line["previousMaintenanceKey"], new_copy))
        except _Skip as reason:
            summary.skipped[str(line.get("id"))] = str(reason)

    # One transaction for the whole file: it only writes one small column, with no
    # object to upload nor anything outside the database to undo, so all or nothing
    # is the simplest state to reason about, and a failed run is just run again.
    with transaction.atomic():
        for root_id, previous_copy, new_copy in checked:
            # Compare and swap: a root whose copy changed since the export (switched
            # to plaintext, re-anchored, backfilled or replaced) keeps it. A queryset
            # update leaves `updated_at` alone, which the batch import compares.
            matching = models.Item.objects.filter(
                pk=root_id, maintenance_wrapped_item_key=previous_copy
            )
            if dry_run:
                found = matching.exists()
            else:
                found = matching.update(maintenance_wrapped_item_key=new_copy)

            if found:
                summary.rotated.append(root_id)
            elif models.Item.objects.filter(pk=root_id).exists():
                summary.skipped[root_id] = "its copy changed since the export"
            else:
                summary.skipped[root_id] = "no longer exists"

    return summary
