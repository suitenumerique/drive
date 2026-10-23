import type { Access, Invitation, User } from "@/features/drivers/types";

type ShareRecipients = {
  userIds: string[];
  emails: string[];
};

const toEmailKey = (email: string) => email.toLowerCase();

// The share modal passes people invited by email as users whose id is their
// email address.
const isEmailOnly = (user: Pick<User, "id" | "email">) =>
  user.email === user.id;

/**
 * Turns the users picked in the share modal into the accesses and invitations
 * to create, leaving out the ones the backend would reject as duplicates.
 */
export const getShareRecipients = (
  users: Pick<User, "id" | "email">[],
  accesses: Pick<Access, "user" | "is_explicit">[],
  invitations: Pick<Invitation, "email">[],
): ShareRecipients => {
  const explicitUserIds = new Set(
    accesses
      .filter((access) => access.is_explicit)
      .map((access) => access.user.id),
  );

  // An email cannot be invited when it belongs to a registered user (picked
  // or already a member) or already has a pending invitation.
  const knownEmails = new Set(
    [
      ...users.filter((user) => !isEmailOnly(user)).map((user) => user.email),
      ...accesses.map((access) => access.user.email),
      ...invitations.map((invitation) => invitation.email),
    ].map(toEmailKey),
  );

  const userIds = new Set<string>();
  const emails = new Set<string>();

  users.forEach((user) => {
    if (!isEmailOnly(user)) {
      // Users with an inherited access only are kept: sharing with them
      // creates their explicit access on this item.
      if (!explicitUserIds.has(user.id)) {
        userIds.add(user.id);
      }
      return;
    }

    const email = toEmailKey(user.email);
    if (!knownEmails.has(email)) {
      emails.add(email);
    }
  });

  return { userIds: Array.from(userIds), emails: Array.from(emails) };
};
