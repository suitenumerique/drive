# Batch recovery of encrypted items

When the encryption service runs its maintenance escrow (see the encryption service README, "Maintenance escrow"), every encryption root in Drive carries a second copy of its key, `maintenance_wrapped_item_key`, wrapped for the maintenance key of its owner's organization. That copy lets the organization's custodians decrypt the stored files in batch, offline, without any user taking part: after a general failure of the encryption, or when an organization stops encrypting. It is a temporary mode, for a massive loss; a user who lost their own keys has their own recovery means.

The vault escrows for the organization of the owner it is given, the root's creator. A root encrypted by someone else (an administrator) gets no copy at encryption, since the vault would escrow it for the caller's organization; the copy is then backfilled for the creator the next time a holder opens the tree, as for a root encrypted before the escrow was enabled. A root without a creator gets none. Any user who can write in the tree may fill a missing copy; replacing an existing one takes an owner or an administrator of the root, is accepted only when the new copy is for another maintenance key (a copy for the key already stored is refused with a 409, `maintenance_key_already_stored`), and is logged (a warning with the item id and the ids of the old and new keys). Drive cannot check that a copy is for the right key nor that it wraps the root's key: the key list lives on the encryption service and only the custodians can open a copy. A forged copy only harms a tree its sender can already edit. A share returns a copy too, which Drive does not store: a share changes neither the root key nor its owner.

Two management commands carry Drive's side of the procedure: the first writes the **encrypted export**, the second imports the **decrypted copy** the tool makes of it. The decryption itself happens between them, on an isolated computer, in the maintenance tool (`/public-assets/maintenance-tool.html` on the encryption service).

## 1. Export

```bash
python manage.py maintenance_export --output /mnt/usb/export --fingerprint <the key's 40 digits>
```

It writes `manifest.ndjson` and, beside it, every encrypted file of every encryption root as `files/<item id>`, streamed from the storage to the disk (never whole in memory). The output folder must be empty or not exist yet: the files of an earlier export would pass for this one's. The path is the item's id rather than its object key, which ends with the file's name: no user's file name in the export's paths, and no character a file system or an archive could refuse. The import uploads under new keys anyway. Each tree comes whole: the root with its escrow copy, every folder and file below it, at any depth, with the key wrapped by its parent. An encryption root nested inside another is a tree of its own. Items purged from the database (`hard_deleted_at` set) are left out; items in the trash are kept.

Each file's line also records the stored version it was read from, `objectEtag` and, in a versioned bucket, `objectVersionId`. The tool passes them through unchanged to the decrypted manifest, where the import compares them with the object at the file's key.

- `--fingerprint` keeps only the trees escrowed for one organization's key: its fingerprint, the 40 digits the maintenance tool shows for the phrase and the encryption server logs at startup beside the organization's domains (spaces allowed). Without it, every tree is exported; the tool sets aside, still encrypted, the trees of other keys.
- Trees without an escrow copy (created before the escrow was enabled, or before their owner's domain was covered, and never opened since) are counted: they cannot be recovered this way.
- A file missing from the object storage is named; its tree will stay encrypted (its line has no `objectEtag`).

Carry the folder to the isolated computer, where the custodians pick it in the tool, type their phrase, and get the decrypted copy back (a folder, or a `.zip` to unzip).

## 2. Import

```bash
python manage.py maintenance_import /mnt/usb/decrypted --dry-run
python manage.py maintenance_import /mnt/usb/decrypted
```

Each tree goes back to plaintext in its own transaction, as the remove-encryption endpoint does it:

1. its decrypted files are uploaded under new object keys (objects are never overwritten), next to the ciphertext, named `<new folder>/<title>` (a title too long for `Item.filename` is cut, its extension kept; a title of `.` or `..` becomes `file`);
2. one transaction locks the tree's items and checks that the tree is the one exported: the same items (none added, removed, moved out or purged), none edited (`updatedAt`), and every file still the stored version the export read (the ETag and version id of the object at its key, read again from the storage); it then switches the files to their new keys, with the type detected from the plaintext (as an upload does) and the plaintext's size, and clears the encryption fields, the per-user wrapped keys on the root's accesses and the escrow copy;
3. after the commit, the files are sent to malware detection and the old encrypted objects are kept, for an investigation should something look wrong (step 3 deletes them); after a failure, the new objects are deleted and the tree is left as it was.

The object check catches what `updatedAt` cannot: an editor saving in place (OnlyOffice writes each save over the same key, without changing the item). Such a save landing after the switch is refused, since the endpoint handing out its upload URL refuses a file no longer encrypted, and the editor shows the save as failed. A save whose upload URL was handed out before the switch can still land after it, at the old key nothing points to any more: the editor's last few seconds of changes, before it notices the file is no longer encrypted.

A tree that changed since the export, or with any item the tool could not decrypt, stays encrypted, escrow copy included, to be exported again in the next batch. A tree that fails for another reason (a storage or database error) is rolled back, its uploads deleted, and reported with the error, and the import goes on with the next tree. Outer trees switch before the trees nested in them. An inner tree whose outer tree is not in this export (another organization's key, exported with `--key-id`) stays encrypted until that organization's import has switched the outer tree; import it again then. Running the import again is harmless, and it is how an interrupted run is finished: switched trees are reported as already in plaintext, the others are tried again. Folders under `other-keys/` (another organization's trees) are ignored.

`--dry-run` makes every check of a real run (the decrypted files present in the folder, the database, the objects in the storage) and changes nothing. The trees nested in a tree it would switch are checked as a real run would find them, with that tree in plaintext.

## 3. Check, then clean up the objects left behind

```bash
python manage.py delete_orphan_objects
python manage.py delete_orphan_objects --delete
```

Once the batch is checked, delete what the import kept and what an interrupted run left: objects no item points to any more.

- the old encrypted objects of every switched tree, kept by the import for an investigation; no key can open them any more;
- a process stopped between the upload of a tree's decrypted files and its transaction leaves those plaintext files (the rerun uploads them again under other keys);
- objects deleted elsewhere without a version id (the remove-encryption endpoint does so), which in a versioned bucket only hides them: their bytes stay in their past versions.

The command lists every object under `item/` that no item points to (an item in the trash still counts), with all its versions; `--delete` deletes them all, for good. Objects written in the last 48 hours are left alone (`--older-than-hours`), so an encryption or an import in progress, which uploads before switching the item, is not caught in the middle. An object under an item that still exists also waits until the item's own key holds an object and the item has not changed for as long: a rename saves the new name before copying the object to it, so after a failed copy the old key holds the file's only bytes. Each key is checked against the database again right before it is deleted. It applies to whatever left such objects, the remove-encryption endpoint and the encryption of files included.

Delete the encrypted export and the decrypted copy once the import is done: the decrypted copy holds the content in plaintext.


## Rotating the maintenance key

When an organization replaces its maintenance key (a custodian leaves, the phrase may have leaked, or on a schedule), every existing copy must be re-wrapped for the new key before the old phrase is destroyed. The re-wrap happens offline, in the maintenance tool, which needs the old phrase and the new public key; Drive only exports the copies and writes the new ones back. No file and no content leaves the storage.

1. The custodians generate the new phrase in the tool, and keep it as they kept the old one.
2. The encryption service operator replaces the organization's public key in `MAINTENANCE_ESCROW_KEYS`. From then on, new roots get copies for the new key, and only the existing copies remain to rotate.
3. Export the copies still escrowed for the old key:

   ```bash
   python manage.py maintenance_export --keys-only --fingerprint <old key's fingerprint> --output /mnt/usb/rotation
   ```

   `--keys-only` writes one line per encryption root, `{"id", "type", "maintenanceKey"}`: no descendant and no file.
4. On the isolated computer, in the tool's "Rotate" tab, the custodians pick the folder, type the old phrase and paste the new public key. The tool writes each line back with `maintenanceKey`, the new copy, and `previousMaintenanceKey`, the exported one, or with `error` for a copy it could not open. Its output holds no secret: carrying it back is no risk.
5. Write the new copies back, after a dry run:

   ```bash
   python manage.py maintenance_rotate /mnt/usb/rotated --dry-run
   python manage.py maintenance_rotate /mnt/usb/rotated
   ```

   The whole file goes in one transaction: it writes a single small column, with nothing in the object storage or elsewhere to undo, so all or nothing is the simplest to reason about, and a failed run is run again. A root's copy is replaced only while it is still the exported one: a root whose copy changed since the export (switched to plaintext, moved, replaced) keeps it. Each new copy is checked as the maintenance-key endpoint checks it, its shape only. The command prints how many roots were rotated, then each root it skipped and why: its copy changed since the export, it no longer exists, or the tool's error. `updated_at` is left alone, so a later batch import does not take the items as edited.
6. Check that nothing is left for the old key: `maintenance_export --keys-only --fingerprint <old key's fingerprint>` must export no copy. A root skipped, or given a copy for the old key meanwhile (a backfill from a browser that still had the old configuration), needs another pass from step 3. Only then destroy the old phrase: until then it still opens any copy left.

## Testing the recovery

`src/backend/core/tests/maintenance_fixture/drive-trees.json` holds encrypted trees exactly as Drive's frontend and the encryption vault store them (a root folder with a subfolder, an image and a PDF, escrowed for the encryption service's development maintenance key, and a file of another organization), with their plaintexts. `test_maintenance_fixture.py` exports them, decrypts them as the tool would from those plaintexts, imports them and reads them back through the API, on every test run: it covers the export and import formats, not the tool. The fixture is written by `generate.mts` beside it, with the encryption service's code, only when the format or the way Drive stores encrypted items changes; its randomness is seeded, so a rerun without a change rewrites the same bytes:

```bash
cd <encryption service checkout> && npx tsx <drive checkout>/src/backend/core/tests/maintenance_fixture/generate.mts
```

The e2e suite's `maintenance-recovery.spec.ts` runs the real maintenance tool on them: seeded for the e2e user, exported in the backend container, decrypted in the tool, the archive imported, then the tree opened in Drive. A second test first rotates the copies to a second development key (`nextMaintenance` in the fixture) through the tool's Rotate tab and `maintenance_rotate`, checks that nothing is left for the old key, then recovers with the new phrase. It is skipped unless `MAINTENANCE_TOOL` names the tool, a path to the built file (`npm run build:maintenance` in the encryption service writes `dist/maintenance/maintenance-tool.html`) or the URL an encryption service serves it at (`https://<interface host>/public-assets/maintenance-tool.html`). With the e2e stack up (`make bootstrap-e2e run-backend-e2e`):

```bash
cd src/frontend/apps/e2e
MAINTENANCE_TOOL=<encryption service checkout>/dist/maintenance/maintenance-tool.html npx playwright test --project=chromium maintenance-recovery
```
