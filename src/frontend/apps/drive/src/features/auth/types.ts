import { Item } from "../drivers/types";

/**
 * Represents user retrieved from the API.
 * @interface User
 * @property {string} id - The id of the user.
 * @property {string} email - The email of the user.
 * @property {string} name - The name of the user.
 */
export interface User {
  id: string;
  email: string;
  language: string | null;
  main_workspace: Item;
  last_release_note_seen?: string | null;
}
