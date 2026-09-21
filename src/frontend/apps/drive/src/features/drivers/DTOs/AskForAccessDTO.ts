import { Role } from "../types";

export type DTOCreateAskForAccess = {
  itemId: string;
  role?: Role;
};

export type DTODeleteAskForAccess = {
  itemId: string;
  askForAccessId: string;
};

export type DTOAcceptAskForAccess = {
  itemId: string;
  askForAccessId: string;
  role?: Role;
};
