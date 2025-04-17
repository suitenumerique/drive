import { Role } from "../types";


export type DTOCreateInvitation = {
  itemId: string;
  email: string;
  role: Role;
};


export type DTOUpdateInvitation = {
  itemId: string;
  invitationId: string;
  role: Role;
};


export type DTODeleteInvitation = {
  itemId: string;
  invitationId: string;
};
