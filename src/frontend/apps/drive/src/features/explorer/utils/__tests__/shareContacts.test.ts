import { Contact, ContactUser } from "@/features/drivers/types";
import {
  expandShareCandidates,
  ShareCandidate,
  toShareCandidates,
} from "../shareContacts";

const GROUP_ID = "6f0c9b2e-3a1d-4c8e-9b7a-2d5e8f1a4c3b";
const OTHER_GROUP_ID = "1b2c3d4e-5f60-4a7b-8c9d-0e1f2a3b4c5d";

const person = (id: string, email: string, full_name = ""): ContactUser => ({
  kind: "user",
  id,
  email,
  full_name,
  short_name: "",
});

describe("toShareCandidates", () => {
  const describeGroup = (count: number | null) => `Group · ${count ?? "?"}`;

  it("keeps people as they are", () => {
    const contacts: Contact[] = [person("u1", "felix@example.org", "Félix")];

    expect(toShareCandidates(contacts, describeGroup)).toEqual([
      {
        id: "u1",
        email: "felix@example.org",
        full_name: "Félix",
        short_name: "",
      },
    ]);
  });

  it("shows a group as one row, its description in place of an email", () => {
    const contacts: Contact[] = [
      {
        kind: "group",
        id: GROUP_ID,
        name: "Design team",
        email: "design@example.org",
        members_count: 12,
      },
    ];

    expect(toShareCandidates(contacts, describeGroup)).toEqual([
      {
        id: `group:${GROUP_ID}`,
        email: "Group · 12",
        full_name: "Design team",
        group_id: GROUP_ID,
      },
    ]);
  });
});

describe("expandShareCandidates", () => {
  const group = (groupId: string): ShareCandidate => ({
    id: `group:${groupId}`,
    email: "Group",
    full_name: "A group",
    group_id: groupId,
  });

  it("leaves people alone and asks for nothing", async () => {
    const getMembers = jest.fn();
    const felix = { id: "u1", email: "felix@example.org", full_name: "Félix" };

    expect(await expandShareCandidates([felix], getMembers)).toEqual([felix]);
    expect(getMembers).not.toHaveBeenCalled();
  });

  it("replaces a group by its members, invitations included", async () => {
    const getMembers = jest
      .fn()
      .mockResolvedValue([
        person("u1", "felix@example.org", "Félix"),
        person("nadia@example.org", "nadia@example.org", "Nadia"),
      ]);

    const people = await expandShareCandidates([group(GROUP_ID)], getMembers);

    expect(getMembers).toHaveBeenCalledWith(GROUP_ID);
    expect(people.map(({ id }) => id)).toEqual(["u1", "nadia@example.org"]);
    expect(people.every((p) => p.group_id === undefined)).toBe(true);
  });

  it("lists each person once", async () => {
    const members: Record<string, ContactUser[]> = {
      [GROUP_ID]: [person("u1", "felix@example.org"), person("u2", "b@x.org")],
      [OTHER_GROUP_ID]: [person("u2", "b@x.org"), person("u3", "c@x.org")],
    };
    const getMembers = jest.fn(async (id: string) => members[id]);

    const people = await expandShareCandidates(
      [
        { id: "u1", email: "felix@example.org", full_name: "Félix" },
        group(GROUP_ID),
        group(OTHER_GROUP_ID),
        group(GROUP_ID),
      ],
      getMembers,
    );

    expect(people.map(({ id }) => id)).toEqual(["u1", "u2", "u3"]);
    expect(getMembers).toHaveBeenCalledTimes(2);
  });

  it("fails when a group's members can't be listed", async () => {
    const getMembers = jest.fn().mockRejectedValue(new Error("unavailable"));

    await expect(
      expandShareCandidates([group(GROUP_ID)], getMembers),
    ).rejects.toThrow("unavailable");
  });
});
