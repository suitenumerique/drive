import {
  DTOCreateAccess,
  DTODeleteAccess,
  DTOUpdateAccess,
} from "./DTOs/AccessesDTO";
import {
  DTOCreateInvitation,
  DTODeleteInvitation,
  DTOUpdateInvitation,
} from "./DTOs/InvitationDTO";
import { Access, APIList, Invitation, Item, ItemType, User } from "./types";

export type ItemFilters = {
  type?: ItemType;
};

export type UserFilters = {
  q?: string;
};

export abstract class Driver {
  abstract getItems(filters?: ItemFilters): Promise<Item[]>;
  abstract getTrashItems(filters?: ItemFilters): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract updateItem(item: Partial<Item>): Promise<Item>;
  abstract restoreItems(ids: string[]): Promise<void>;
  abstract moveItem(id: string, parentId: string): Promise<void>;
  abstract moveItems(ids: string[], parentId: string): Promise<void>;
  abstract getChildren(id: string, filters?: ItemFilters): Promise<Item[]>;
  // Accesses
  abstract getItemAccesses(itemId: string): Promise<APIList<Access>>;
  abstract createAccess(data: DTOCreateAccess): Promise<void>;
  abstract updateAccess(payload: DTOUpdateAccess): Promise<Access>;
  abstract deleteAccess(payload: DTODeleteAccess): Promise<void>;
  // Invitations
  abstract getItemInvitations(itemId: string): Promise<APIList<Invitation>>;
  abstract createInvitation(data: DTOCreateInvitation): Promise<Invitation>;
  abstract deleteInvitation(payload: DTODeleteInvitation): Promise<void>;
  abstract updateInvitation(payload: DTOUpdateInvitation): Promise<Invitation>;

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
  abstract hardDeleteItems(ids: string[]): Promise<void>;
}
