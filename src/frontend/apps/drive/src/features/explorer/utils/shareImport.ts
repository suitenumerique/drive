import type { i18n as I18n } from "i18next";
import { Role } from "@/features/drivers/types";
import { LANGUAGES } from "@/features/i18n/conf";

/** Lowercases a role name and strips its accents ("Éditeur" -> "editeur"). */
const normalizeRoleName = (role: string) =>
  role
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

/**
 * Returns a function converting a role name from an imported contacts file
 * to a role value. Users know the roles by the names the UI shows them, so
 * besides the role values ("reader"), the file accepts the role names of
 * every language we ship ("Lecteur", "Lezer"...), regardless of their case
 * and accents. Unknown roles are returned as is, the backend rejects them.
 */
export const createImportRoleResolver = (i18n: I18n) => {
  const roles = Object.values(Role);
  const rolesByName = new Map<string, Role>();
  for (const language of LANGUAGES) {
    const t = i18n.getFixedT(language.value);
    for (const role of roles) {
      rolesByName.set(normalizeRoleName(t(`roles.${role}`)), role);
    }
  }
  // Set last so a translation can never shadow a role value.
  for (const role of roles) {
    rolesByName.set(role, role);
  }

  return (role: string): Role =>
    rolesByName.get(normalizeRoleName(role)) ?? (role as Role);
};
