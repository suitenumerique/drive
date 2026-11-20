import { describe, expect, it, jest } from "@jest/globals";

import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import { getItemIconAltKey } from "../mimeTypes";

jest.mock("@/features/config/Config", () => ({ getDriver: jest.fn() }));
jest.mock("@/features/i18n/initI18n", () => ({ t: (key: string) => key }));

const item = (overrides: Partial<Item>): Item =>
  ({
    id: "1",
    title: "Report.pdf",
    filename: "Report.pdf",
    type: ItemType.FILE,
    mimetype: "application/pdf",
    upload_state: ItemUploadState.READY,
    ...overrides,
  }) as Item;

describe("getItemIconAltKey", () => {
  it("describes a folder, even when its name looks like a file", () => {
    expect(
      getItemIconAltKey(
        item({
          type: ItemType.FOLDER,
          title: "Notes.pdf",
          filename: "Notes.pdf",
        }),
        "Notes.pdf",
      ),
    ).toBe("explorer.grid.columns.folder");
  });

  it("describes a restricted folder with its own icon", () => {
    expect(
      getItemIconAltKey(
        item({
          type: ItemType.FOLDER,
          is_restricted: true,
          title: "Private",
          filename: "Private",
        }),
        "Private",
      ),
    ).toBe("explorer.grid.item_icon_alt.restricted_folder");
  });

  it("describes a file whose extension was removed from the visible name", () => {
    expect(getItemIconAltKey(item({}), "Report")).toBe("mime.pdf");
  });

  it("leaves the icon decorative when the visible name already ends with the extension", () => {
    expect(getItemIconAltKey(item({}), "Report.pdf")).toBeNull();
  });

  it("describes a suspicious file from the icon, not from the mime type", () => {
    expect(
      getItemIconAltKey(
        item({ upload_state: ItemUploadState.SUSPICIOUS }),
        "Report.pdf",
      ),
    ).toBe("explorer.grid.item_icon_alt.suspicious");
  });

  it("follows the title extension when the filename extension differs", () => {
    expect(
      getItemIconAltKey(
        item({
          title: "x",
          filename: "x.grist",
          mimetype: "application/vnd.sqlite3",
        }),
        "x",
      ),
    ).toBe("explorer.grid.item_icon_alt.sqlite");
  });

  it("describes a file that has no extension in its name", () => {
    expect(
      getItemIconAltKey(
        item({
          title: "notes",
          filename: "notes",
          mimetype: "text/plain",
        }),
        "notes",
      ),
    ).toBe("mime.other");
  });
});
