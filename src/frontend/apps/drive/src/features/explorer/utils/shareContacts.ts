import { Contact, ContactUser } from "@/features/drivers/types";

/**
 * A row of the share modal: a person, or a group shown as one row.
 *
 * The modal has no notion of groups: it lists rows with a name and an email,
 * and turns a row whose id is its email into an invitation.
 */
export type ShareCandidate = {
  id: string;
  email: string;
  full_name: string;
  short_name?: string;
  // Set on a group row: the group's id at the contact search backend.
  group_id?: string;
};

// Keeps group rows apart from users (uuid ids) and invitations (email ids).
const GROUP_ROW_PREFIX = "group:";

/**
 * The contact search results as share modal rows.
 *
 * @param describeGroup What to show under a group's name, in place of an
 * email (e.g. "Group · 12 members").
 */
export const toShareCandidates = (
  contacts: Contact[],
  describeGroup: (membersCount: number | null) => string,
): ShareCandidate[] =>
  contacts.map((contact) =>
    contact.kind === "group"
      ? {
          id: `${GROUP_ROW_PREFIX}${contact.id}`,
          email: describeGroup(contact.members_count),
          full_name: contact.name,
          group_id: contact.id,
        }
      : {
          id: contact.id,
          email: contact.email,
          full_name: contact.full_name,
          short_name: contact.short_name,
        },
  );

/**
 * The people to share with: the picked rows, groups replaced by their members.
 *
 * Each person comes once, even when picked alone and through a group, or
 * through several groups.
 */
export const expandShareCandidates = async (
  candidates: ShareCandidate[],
  getGroupMembers: (groupId: string) => Promise<ContactUser[]>,
): Promise<ShareCandidate[]> => {
  const groupIds = [
    ...new Set(
      candidates.flatMap((candidate) =>
        candidate.group_id ? [candidate.group_id] : [],
      ),
    ),
  ];
  const members = await Promise.all(
    groupIds.map((groupId) => getGroupMembers(groupId)),
  );

  const people = new Map<string, ShareCandidate>();
  const add = (person: ShareCandidate) => {
    if (!people.has(person.id)) {
      people.set(person.id, person);
    }
  };
  candidates.filter((candidate) => !candidate.group_id).forEach(add);
  members.flat().forEach((member) =>
    add({
      id: member.id,
      email: member.email,
      full_name: member.full_name,
      short_name: member.short_name,
    }),
  );
  return [...people.values()];
};
