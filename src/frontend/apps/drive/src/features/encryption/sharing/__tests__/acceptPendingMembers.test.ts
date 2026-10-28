import { Access } from "@/features/drivers/types";
import { acceptPendingMembers } from "../acceptPendingMembers";
import { fetchChainKey } from "../wrapKeyForUser";

const driver = {
  getKeyChain: jest.fn(),
  acceptEncryptionAccess: jest.fn(),
};
jest.mock("@/features/config/Config", () => ({ getDriver: () => driver }));
jest.mock("@/features/encryption/fetchRegisteredKeys", () => ({
  fetchRegisteredKeys: async (subs: string[]) => ({
    publicKeys: Object.fromEntries(
      subs.filter((sub) => sub !== "not-ready").map((sub) => [sub, "PK"]),
    ),
    versions: Object.fromEntries(subs.map((sub) => [sub, 7])),
  }),
}));
jest.mock("@/features/explorer/hooks/useRefreshItems", () => ({}));

const bytes = (buffer: ArrayBuffer) =>
  btoa(String.fromCharCode(...new Uint8Array(buffer)));

// The caller enters at `root`; the chain goes root > folder > file.
const KEY_CHAIN = {
  user_access_item_id: "root",
  encrypted_key_for_user: btoa("ENTRY"),
  encryption_public_key_version: 1,
  chain: [
    { item_id: "folder", encrypted_symmetric_key: btoa("FOLDER") },
    { item_id: "file", encrypted_symmetric_key: btoa("FILE") },
  ],
};

const access = (sub: string, itemId: string) =>
  ({
    id: `access-${sub}`,
    user: { id: `id-${sub}`, sub, email: `${sub}@example.org`, full_name: sub },
    item: { id: itemId },
  }) as unknown as Access;

beforeEach(() => {
  jest.clearAllMocks();
  driver.getKeyChain.mockResolvedValue(KEY_CHAIN);
});

describe("fetchChainKey", () => {
  it("resolves an item of the chain through the chain down to it, and a higher one to the entry point", async () => {
    const keys = await fetchChainKey("file", ["folder", "workspace"]);

    const folder = keys.get("folder")!;
    expect(folder.itemId).toBe("folder");
    expect(folder.encryptedKeyChain!.map(bytes)).toEqual([btoa("FOLDER")]);

    const workspace = keys.get("workspace")!;
    expect(workspace.itemId).toBe("root");
    expect(workspace.encryptedKeyChain).toBeUndefined();
    expect(bytes(workspace.entryKey)).toBe(btoa("ENTRY"));
  });
});

describe("acceptPendingMembers", () => {
  it("gives each member the key of the item their access is on, never a higher one", async () => {
    const shareKeys = jest.fn(
      async (
        _key: ArrayBuffer,
        recipients: Record<string, unknown>,
        _chain?: ArrayBuffer[],
      ) => ({
        encryptedKeys: Object.fromEntries(
          Object.keys(recipients).map((sub) => [
            sub,
            new TextEncoder().encode(`WRAP-${sub}`).buffer,
          ]),
        ),
      }),
    );
    // Node tests: the vault client is read from `window`.
    Object.assign(globalThis, {
      window: { __driveVaultClient: { shareKeys } },
    });

    const { accepted, notReady } = await acceptPendingMembers("file", [
      access("alice", "workspace"),
      access("bob", "folder"),
      access("not-ready", "folder"),
    ]);

    expect(accepted.map((a) => a.user.sub)).toEqual(["alice", "bob"]);
    expect(notReady.map((a) => a.user.sub)).toEqual(["not-ready"]);
    // One vault call per key: the entry point's, then the folder's.
    expect(shareKeys.mock.calls.map((call) => call[2]?.map(bytes))).toEqual([
      undefined,
      [btoa("FOLDER")],
    ]);
    expect(driver.acceptEncryptionAccess.mock.calls).toEqual([
      [
        "root",
        {
          user_id: "id-alice",
          encrypted_item_symmetric_key_for_user: btoa("WRAP-alice"),
          encryption_public_key_version: 7,
        },
      ],
      [
        "folder",
        {
          user_id: "id-bob",
          encrypted_item_symmetric_key_for_user: btoa("WRAP-bob"),
          encryption_public_key_version: 7,
        },
      ],
    ]);
  });
});
