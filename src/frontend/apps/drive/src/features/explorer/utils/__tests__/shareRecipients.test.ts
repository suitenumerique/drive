import { getShareRecipients } from "../shareRecipients";

const alice = { id: "alice-id", email: "alice@example.com" };
const bob = { id: "bob-id", email: "bob@example.com" };

// The share modal passes people invited by email with their email as id.
const byEmail = (email: string) => ({ id: email, email });

const access = (user: typeof alice, is_explicit: boolean) => ({
  user: { ...user, full_name: "", short_name: "", language: "" },
  is_explicit,
});

describe("getShareRecipients", () => {
  it("splits registered users from people invited by email", () => {
    expect(
      getShareRecipients([alice, byEmail("new@example.com")], [], []),
    ).toEqual({ userIds: ["alice-id"], emails: ["new@example.com"] });
  });

  it("invites an email typed twice only once, whatever its case", () => {
    expect(
      getShareRecipients(
        [byEmail("new@example.com"), byEmail("New@Example.com")],
        [],
        [],
      ),
    ).toEqual({ userIds: [], emails: ["new@example.com"] });
  });

  it("shares with a user picked twice only once", () => {
    expect(getShareRecipients([alice, { ...alice }], [], [])).toEqual({
      userIds: ["alice-id"],
      emails: [],
    });
  });

  it("does not invite the email of a user picked by name", () => {
    expect(
      getShareRecipients([alice, byEmail("ALICE@example.com")], [], []),
    ).toEqual({ userIds: ["alice-id"], emails: [] });
  });

  it("leaves out users that already have an explicit access", () => {
    expect(
      getShareRecipients(
        [alice, byEmail("alice@example.com")],
        [access(alice, true)],
        [],
      ),
    ).toEqual({ userIds: [], emails: [] });
  });

  it("keeps users whose access is only inherited", () => {
    expect(getShareRecipients([bob], [access(bob, false)], [])).toEqual({
      userIds: ["bob-id"],
      emails: [],
    });
  });

  it("does not invite an email that is already invited", () => {
    expect(
      getShareRecipients(
        [byEmail("Pending@example.com")],
        [],
        [{ email: "pending@example.com" }],
      ),
    ).toEqual({ userIds: [], emails: [] });
  });
});
