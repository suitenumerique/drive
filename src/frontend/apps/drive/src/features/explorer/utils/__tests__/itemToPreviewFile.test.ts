import { Item, ItemType } from "@/features/drivers/types";
import {
  getNavigableItem,
  isFolderAccessDenied,
} from "@/features/drivers/utils";
import { itemToPreviewFile } from "../utils";

jest.mock("@/features/config/Config", () => ({ getDriver: jest.fn() }));
jest.mock("@/features/i18n/initI18n", () => ({ t: (key: string) => key }));

const folder = {
  id: "folder",
  title: "Top.secret.pdf",
  type: ItemType.FOLDER,
  abilities: {},
} as Item;

const restriction: Item = {
  ...folder,
  id: "restriction",
  type: ItemType.RESTRICTION,
  target: {
    id: folder.id,
    title: folder.title,
    path: "folder",
    is_restricted: true,
    can_access: false,
    deleted: false,
    abilities: folder.abilities,
  },
};

describe("folder preview access", () => {
  it("previews an inaccessible restriction using its entry ID and full name", () => {
    expect(isFolderAccessDenied(restriction)).toBe(true);
    expect(getNavigableItem(restriction)).toBeUndefined();
    expect(itemToPreviewFile(restriction)).toMatchObject({
      id: restriction.id,
      title: "Top.secret.pdf",
      isFolderAccessDenied: true,
      mimetype: "",
      url: "",
      url_preview: "",
      size: 0,
    });
  });

  it("does not pass stale content URLs or metadata to a denied folder preview", () => {
    expect(
      itemToPreviewFile({
        ...restriction,
        mimetype: "application/pdf",
        url: "/original.pdf",
        url_preview: "/preview.pdf",
        size: 100,
      }),
    ).toMatchObject({
      isFolderAccessDenied: true,
      mimetype: "",
      url: "",
      url_preview: "",
      size: 0,
    });
  });

  it.each([false, true])(
    "keeps normal folder navigation when is_restricted is %s",
    (is_restricted) => {
      const item = { ...folder, is_restricted };
      expect(isFolderAccessDenied(item)).toBe(false);
      expect(itemToPreviewFile(item).isFolderAccessDenied).toBe(false);
      expect(getNavigableItem(item)).toBe(item);
    },
  );

  it("navigates to the target of an accessible restriction", () => {
    const item = {
      ...restriction,
      target: { ...restriction.target!, can_access: true },
    };
    expect(isFolderAccessDenied(item)).toBe(false);
    expect(getNavigableItem(item)).toMatchObject({ id: folder.id });
  });

  it.each([null, { ...restriction.target!, deleted: true }])(
    "keeps missing or deleted targets unavailable",
    (target) => {
      const item = { ...restriction, target };
      expect(isFolderAccessDenied(item)).toBe(false);
      expect(getNavigableItem(item)).toBeUndefined();
    },
  );

  it("preserves file metadata and keeps the denied-folder flag off", () => {
    const item = {
      ...folder,
      type: ItemType.FILE,
      mimetype: "application/pdf",
      url: "/original.pdf",
      url_preview: "/preview.pdf",
      size: 100,
    };
    expect(itemToPreviewFile(item)).toMatchObject({
      id: item.id,
      mimetype: item.mimetype,
      url: item.url,
      url_preview: item.url_preview,
      size: item.size,
      isFolderAccessDenied: false,
    });
  });
});
