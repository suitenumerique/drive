import { AccessRequestStatus, LinkReach, LinkRole, Role } from "../types";

export type DTOCreateAccess = {
  itemId: string;
  userId: string;
  role: Role;
};

export type DTOCreateAccessRequest = {
  itemId: string;
  message?: string;
};

export type DTOUpdateAccessRequest = {
  itemId: string;
  accessRequestId: string;
  status: AccessRequestStatus;
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

export type DTOBatchShare = {
  itemId: string;
  rows: {
    email: string;
    role: Role;
  }[];
};

export type DTOUpdateLinkConfiguration = {
  itemId: string;
  link_reach: LinkReach;
  link_role?: LinkRole | null;
};
