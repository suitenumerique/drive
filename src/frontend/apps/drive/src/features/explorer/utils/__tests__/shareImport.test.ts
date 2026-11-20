import i18next from "i18next";
import { Role } from "@/features/drivers/types";
import { i18nOptions } from "@/features/i18n/options";
import { createImportRoleResolver } from "../shareImport";

describe("createImportRoleResolver", () => {
  let toImportRole: (role: string) => Role;

  beforeAll(async () => {
    // The real translations are used so that any language added to the app
    // is accepted by the import without touching this code.
    const instance = i18next.createInstance();
    await instance.init(i18nOptions);
    toImportRole = createImportRoleResolver(instance);
  });

  it.each([
    ["reader", Role.READER],
    ["editor", Role.EDITOR],
    ["administrator", Role.ADMIN],
    ["owner", Role.OWNER],
  ])("keeps the role value %s", (role, expected) => {
    expect(toImportRole(role)).toBe(expected);
  });

  it.each([
    ["Lecteur", Role.READER],
    ["Éditeur", Role.EDITOR],
    ["Administrateur", Role.ADMIN],
    ["Propriétaire", Role.OWNER],
    ["Lezer", Role.READER],
    ["Redacteur", Role.EDITOR],
    ["Beheerder", Role.ADMIN],
    ["Eigenaar", Role.OWNER],
  ])("converts the translated role name %s", (role, expected) => {
    expect(toImportRole(role)).toBe(expected);
  });

  it.each([
    ["Reader", Role.READER],
    [" OWNER ", Role.OWNER],
    ["editeur", Role.EDITOR],
    ["PROPRIETAIRE", Role.OWNER],
  ])("ignores the case, accents and spaces of %s", (role, expected) => {
    expect(toImportRole(role)).toBe(expected);
  });

  it("returns unknown roles as is", () => {
    expect(toImportRole("superuser")).toBe("superuser");
  });
});
