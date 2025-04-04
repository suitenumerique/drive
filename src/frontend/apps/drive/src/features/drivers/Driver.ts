import { Access, Invitation, Item, ItemType, Role, User } from "./types";


export type ItemFilters = {
  type?: ItemType;
};

export type DTOInvitation = {
  member: string;
  role: Role;
};

export type DTOAccess = {
  member: string;
  role: Role;
};

export type UserFilters = {
  q?: string;
  email?: string;
  full_name?: string;
};

export abstract class Driver {
  abstract getItems(filters?: ItemFilters): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract updateItem(item: Partial<Item>): Promise<Item>;
  abstract moveItem(id: string, parentId: string): Promise<void>;
  abstract moveItems(ids: string[], parentId: string): Promise<void>;
  abstract getChildren(id: string, filters?: ItemFilters): Promise<Item[]>;
  // Accesses
  abstract getItemAccesses(itemId: string): Promise<Access[]>;
  // abstract createAccess(data: DTOAccess): Promise<Access>;
  // abstract updateAccess(itemId: string,accessId: string, data: DTOAccess): Promise<Access>;
  // abstract deleteAccess(accessId: string): Promise<void>;
  // Invitations
  abstract getItemInvitations(itemId: string): Promise<Invitation[]>;
  // abstract createInvitation(data: DTOInvitation): Promise<Invitation>;
  // abstract deleteInvitation(invitationId: string): Promise<void>;
  // abstract updateInvitation(invitationId: string, data: DTOInvitation): Promise<Invitation>;

  // Users
  abstract getUsers(filters?: UserFilters): Promise<User[]>;
  // Tree
  abstract getTree(id: string): Promise<Item>;
  abstract createFolder(data: { title: string }): Promise<Item>;
  abstract createWorkspace(data: {
    title: string;
    description: string;
  }): Promise<Item>;
  abstract updateWorkspace(item: Partial<Item>): Promise<Item>;
  abstract deleteWorkspace(id: string): Promise<void>;
  abstract createFile(data: {
    parentId: string;
    filename: string;
  }): Promise<Item>;
  abstract deleteItems(ids: string[]): Promise<void>;
}
