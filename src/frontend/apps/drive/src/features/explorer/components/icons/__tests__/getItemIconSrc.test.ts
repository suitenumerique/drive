import { ICONS, MimeCategory } from "@gouvfr-lasuite/ui-components";
import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import { getItemExtendedIcon, getItemIconSrc } from "../ItemIcon";

jest.mock("@/features/config/Config", () => ({ getDriver: jest.fn() }));
jest.mock("@/features/i18n/initI18n", () => ({ t: (key: string) => key }));

const file = (mimetype: string, title: string): Item =>
  ({
    id: title,
    title,
    filename: title,
    type: ItemType.FILE,
    mimetype,
    upload_state: ItemUploadState.READY,
    abilities: {},
  }) as Item;

describe("getItemIconSrc", () => {
  it("gives the icon of the file's type", () => {
    expect(
      getItemIconSrc(
        file(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "Budget.xlsx",
        ),
      ),
    ).toBe(ICONS.normal[MimeCategory.CALC]);
    expect(getItemIconSrc(file("application/pdf", "Report.pdf"))).toBe(
      ICONS.normal[MimeCategory.PDF],
    );
  });

  it("gives the mini icon when asked", () => {
    expect(getItemIconSrc(file("application/pdf", "Report.pdf"), "mini")).toBe(
      ICONS.mini[MimeCategory.PDF],
    );
  });

  it("gives drive's own icon for folders and suspicious files", () => {
    const folder = { ...file("", "Folder"), type: ItemType.FOLDER } as Item;
    expect(getItemIconSrc(folder)).toBe(getItemExtendedIcon(folder, "normal"));

    const suspicious = {
      ...file("application/pdf", "Report.pdf"),
      upload_state: ItemUploadState.SUSPICIOUS,
    } as Item;
    expect(getItemIconSrc(suspicious)).toBe(
      ICONS.normal[MimeCategory.SUSPICIOUS],
    );
  });
});
