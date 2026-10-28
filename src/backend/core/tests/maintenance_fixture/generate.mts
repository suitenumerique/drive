/**
 * Writes `drive-trees.json` beside this file: encrypted Drive trees, exactly as
 * Drive's frontend and the encryption vault store them, with the maintenance escrow
 * copy of each root, for the batch recovery tests (`test_maintenance_fixture.py`
 * without a browser, `maintenance-recovery.spec.ts` in the e2e app with the real
 * maintenance tool). Data only: the rows, the objects and the plaintexts they hold.
 *
 * Run by hand, only when the export format or the way Drive stores encrypted items
 * changes, from a checkout of the encryption service (its crypto code, its `tsx`
 * and its `@encryption/src/...` paths):
 *
 *   cd <encryption checkout> && npx tsx <drive checkout>/src/backend/core/tests/maintenance_fixture/generate.mts
 *
 * The randomness is seeded, here only: a rerun without a change rewrites the same
 * bytes, so the diff shows only what really changed. Keys and nonces derived from a
 * public seed are fine for fake content under the development maintenance phrase.
 *
 * What it holds, as Drive stores it:
 *   - a root folder for the DEV maintenance key: no per-item wrap
 *     (`encrypted_symmetric_key` empty), its key wrapped for its owner on the
 *     owner's access (X-Wing, for a device key that no longer exists, which is what
 *     a batch recovery is for) and for the maintenance key in
 *     `maintenance_wrapped_item_key`, both base64;
 *   - below it, a subfolder and two files: each item's key wrapped by its parent's
 *     (`DOMAIN_WRAPPED_KEY`) in `encrypted_symmetric_key`, base64; each file's bytes
 *     encrypted with its own key (`DOMAIN_CONTENT`), raw in the object storage at
 *     `item/<id>/<filename>`, with the type and size an encrypted upload leaves;
 *   - an encrypted file of another organization, its own root, escrowed for
 *     another maintenance key: an export for the DEV fingerprint leaves it out;
 *   - a second development key (`nextMaintenance`), which nothing is escrowed for:
 *     the rotation test moves the DEV copies to it.
 */
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

let counter = 0;

// libsodium draws every random byte from here: replaced before it loads (hence the dynamic imports below).
Object.defineProperty(globalThis.crypto, 'getRandomValues', {
  configurable: true,
  value: <T extends ArrayBufferView>(array: T): T => {
    const bytes = new Uint8Array(array.buffer, array.byteOffset, array.byteLength);

    for (let offset = 0; offset < bytes.length; offset += 32) {
      bytes.set(
        createHash('sha256')
          .update(`lasuite-drive-maintenance-fixture:${counter++}`)
          .digest()
          .subarray(0, bytes.length - offset),
        offset
      );
    }

    return array;
  },
});

const { encryptContent, encryptSymmetricKeyForUsers, generateSymmetricKey, generateUserKeyPair, uint8ToBase64, wrapKeyForMaintenance } = await import(
  '@encryption/src/crypto'
);
const { importMaintenancePublicKey, maintenanceKeyIdToFingerprint } = await import('@encryption/src/crypto/maintenance-escrow');
const { DEV_MAINTENANCE_PHRASE, DEV_MAINTENANCE_PUBLIC_KEY, DEV_NEXT_MAINTENANCE_PHRASE, DEV_NEXT_MAINTENANCE_PUBLIC_KEY } = await import(
  '@encryption/src/maintenance/dev-maintenance-key'
);
const { SAMPLE_IMAGES, sampleOtherOrganizationKey } = await import('@encryption/src/maintenance/testing');
const { DOMAIN_CONTENT, DOMAIN_KEM_DOCUMENT_KEY, DOMAIN_WRAPPED_KEY } = await import('@encryption/src/shared/crypto-domains');

/** A one-page PDF showing `text`: what the preview renders, small enough to read in the fixture. */
function onePagePdf(text: string): Uint8Array {
  const stream = `BT /F1 18 Tf 72 720 Td (${text}) Tj ET`;
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = objects.map((body, index) => {
    const offset = pdf.length;
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`;
    return offset;
  });
  const xref = pdf.length;

  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('');
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;

  return new TextEncoder().encode(pdf);
}

const MINUTES_TEXT = 'Budget 2027: minutes of the steering committee';

const ids = {
  budget: 'd7e00000-0000-4000-8000-000000000001',
  annexes: 'd7e00000-0000-4000-8000-000000000002',
  invoice: 'd7e00000-0000-4000-8000-000000000003',
  minutes: 'd7e00000-0000-4000-8000-000000000004',
  elsewhere: 'd7e00000-0000-4000-8000-000000000005',
};

const plaintexts: Record<string, Uint8Array> = {
  [ids.invoice]: SAMPLE_IMAGES.green,
  [ids.minutes]: onePagePdf(MINUTES_TEXT),
  [ids.elsewhere]: SAMPLE_IMAGES.grey,
};

const devKey = await importMaintenancePublicKey(DEV_MAINTENANCE_PUBLIC_KEY);
const otherKey = await sampleOtherOrganizationKey();
// The owner's device key: its secret is dropped, as a lost device's would be.
const ownerDevice = await generateUserKeyPair();
const [budget, annexes, invoice, minutes, elsewhere] = await Promise.all(Array.from({ length: 5 }, () => generateSymmetricKey()));

const b64 = (bytes: Uint8Array) => uint8ToBase64(bytes);
const wrapped = async (child: Uint8Array, parent: Uint8Array) => b64(await encryptContent(child, parent, DOMAIN_WRAPPED_KEY));
const forOwner = async (key: Uint8Array) => b64((await encryptSymmetricKeyForUsers(key, { owner: ownerDevice.publicKey }, DOMAIN_KEM_DOCUMENT_KEY)).owner);
const sealed = (id: string, key: Uint8Array) => encryptContent(plaintexts[id], key, DOMAIN_CONTENT);

const items: Record<string, unknown>[] = [];
const accesses: Record<string, unknown>[] = [];
const objects: Record<string, string> = {};

async function root(id: string, fields: Record<string, unknown>, key: Uint8Array, maintenanceKey: typeof devKey) {
  items.push({
    id,
    parent: null,
    ...fields,
    link_reach: 'restricted',
    is_encrypted: true,
    encrypted_symmetric_key: null,
    maintenance_wrapped_item_key: b64(await wrapKeyForMaintenance(key, maintenanceKey)),
  });
  accesses.push({ item: id, role: 'owner', encrypted_item_symmetric_key_for_user: await forOwner(key), encryption_public_key_version: 1 });
}

function folder(id: string, parent: string, title: string, wrappedKey: string) {
  items.push({ id, parent, type: 'folder', title, link_reach: null, is_encrypted: true, encrypted_symmetric_key: wrappedKey });
}

async function file(id: string, title: string, key: Uint8Array) {
  const ciphertext = await sealed(id, key);

  objects[`item/${id}/${title}`] = b64(ciphertext);

  // What an encrypted upload leaves: the file name as given, the ciphertext's type and size.
  return { type: 'file', title, filename: title, upload_state: 'ready', mimetype: 'application/octet-stream', size: ciphertext.length };
}

await root(ids.budget, { type: 'folder', title: 'Budget 2027' }, budget, devKey);
folder(ids.annexes, ids.budget, 'Annexes', await wrapped(annexes, budget));
items.push({
  id: ids.invoice,
  parent: ids.annexes,
  ...(await file(ids.invoice, 'facture.png', invoice)),
  link_reach: null,
  is_encrypted: true,
  encrypted_symmetric_key: await wrapped(invoice, annexes),
});
items.push({
  id: ids.minutes,
  parent: ids.budget,
  ...(await file(ids.minutes, 'compte-rendu.pdf', minutes)),
  link_reach: null,
  is_encrypted: true,
  encrypted_symmetric_key: await wrapped(minutes, budget),
});
await root(ids.elsewhere, await file(ids.elsewhere, 'photo.png', elsewhere), elsewhere, otherKey);

const fixture = {
  _comment: 'Generated by generate.mts beside this file (see its header): do not edit by hand.',
  maintenance: {
    phrase: DEV_MAINTENANCE_PHRASE,
    fingerprint: maintenanceKeyIdToFingerprint(devKey.keyId),
    roots: [ids.budget],
  },
  // The key the rotation test moves the copies to: the tool needs its public key, the recovery after it its phrase.
  nextMaintenance: {
    phrase: DEV_NEXT_MAINTENANCE_PHRASE,
    publicKey: DEV_NEXT_MAINTENANCE_PUBLIC_KEY,
    fingerprint: maintenanceKeyIdToFingerprint((await importMaintenancePublicKey(DEV_NEXT_MAINTENANCE_PUBLIC_KEY)).keyId),
  },
  otherOrganization: { fingerprint: maintenanceKeyIdToFingerprint(otherKey.keyId), roots: [ids.elsewhere] },
  minutesText: MINUTES_TEXT,
  items,
  accesses,
  objects,
  plaintexts: Object.fromEntries(Object.entries(plaintexts).map(([id, bytes]) => [id, b64(bytes)])),
};

const output = resolve(import.meta.dirname, 'drive-trees.json');

writeFileSync(output, `${JSON.stringify(fixture, null, 2)}\n`);
console.log(`Fixture written to ${output}`);
