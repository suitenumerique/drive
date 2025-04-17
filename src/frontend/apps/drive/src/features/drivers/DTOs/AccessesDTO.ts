import { Role } from "../types";

export type DTOCreateAccess = {
    itemId: string;
    userId: string;
    role: Role;  
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
}