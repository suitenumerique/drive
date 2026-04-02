import { LinkReach, LinkRole, Role } from "../types";

export type DTOCreateAccess = {
  itemId: string;
  userId: string;
  role: Role;
  encrypted_item_symmetric_key_for_user?: string;
  encryption_public_key_fingerprint?: string;
};

export type DTOUpdateAccess = {
  itemId: string;
  accessId: string;
  user_id: string;
  role: Role;
};

export type DTODeleteAccess = {
  itemId: string;
  accessId: string;
};

export type DTOUpdateLinkConfiguration = {
  itemId: string;
  link_reach: LinkReach;
  link_role?: LinkRole | null;
};
