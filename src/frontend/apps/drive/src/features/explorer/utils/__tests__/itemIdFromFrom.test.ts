import { itemIdFromFrom } from "@/pages/403";

const UUID = "550e8400-e29b-41d4-a716-446655440000";

describe("itemIdFromFrom", () => {
  it("returns null when from is undefined", () => {
    expect(itemIdFromFrom(undefined)).toBeNull();
  });

  it("returns null when the URL matches no known pattern", () => {
    expect(itemIdFromFrom("/some/other/path")).toBeNull();
  });

  it("extracts the item id from a folder URL", () => {
    expect(itemIdFromFrom(`/explorer/items/${UUID}`)).toBe(UUID);
  });

  it("extracts the item id from a file preview URL", () => {
    expect(itemIdFromFrom(`/explorer/items/files/${UUID}`)).toBe(UUID);
  });

  it("extracts the item id from a wopi URL", () => {
    expect(itemIdFromFrom(`/wopi/${UUID}`)).toBe(UUID);
  });

  it("handles an array by using the first entry", () => {
    expect(itemIdFromFrom([`/explorer/items/${UUID}`, "/other"])).toBe(UUID);
  });

  it("handles a URL-encoded from value", () => {
    expect(itemIdFromFrom(encodeURIComponent(`/explorer/items/${UUID}`))).toBe(
      UUID,
    );
  });

  it("returns null on a malformed URL-encoded value", () => {
    expect(itemIdFromFrom("%zz")).toBeNull();
  });
});
