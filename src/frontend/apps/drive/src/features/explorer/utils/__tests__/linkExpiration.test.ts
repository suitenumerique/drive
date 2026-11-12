import { LinkReach, LinkRole } from "@/features/drivers/types";
import {
  canLinkExpire,
  getLinkExpirationReset,
  isLinkExpired,
} from "../linkExpiration";

const link = (
  link_reach: LinkReach | undefined,
  link_role: LinkRole | undefined,
  ancestors_link_reach: LinkReach | null = null,
  ancestors_link_role: LinkRole | null = null,
) => ({
  link_reach,
  link_role,
  link_expires_at: null,
  ancestors_link_reach,
  ancestors_link_role,
});

describe("isLinkExpired", () => {
  const now = new Date("2026-11-10T12:00:00Z");

  it("is false without an expiration date", () => {
    expect(isLinkExpired({ link_expires_at: null }, now)).toBe(false);
    expect(isLinkExpired({}, now)).toBe(false);
  });

  it("is false for a future date", () => {
    expect(
      isLinkExpired({ link_expires_at: "2026-11-11T00:00:00Z" }, now),
    ).toBe(false);
  });

  it("is true for a past or current date", () => {
    expect(
      isLinkExpired({ link_expires_at: "2020-01-01T00:00:00Z" }, now),
    ).toBe(true);
    expect(isLinkExpired({ link_expires_at: now.toISOString() }, now)).toBe(
      true,
    );
  });
});

describe("getLinkExpirationReset", () => {
  it("clears a past date", () => {
    expect(
      getLinkExpirationReset({ link_expires_at: "2020-01-01T00:00:00Z" }),
    ).toEqual({ link_expires_at: null });
  });

  it("keeps a future or missing date", () => {
    expect(
      getLinkExpirationReset({ link_expires_at: "2999-01-01T00:00:00Z" }),
    ).toEqual({});
    expect(getLinkExpirationReset({ link_expires_at: null })).toEqual({});
  });
});

describe("canLinkExpire", () => {
  it("is false for a restricted or unset link", () => {
    expect(canLinkExpire(link(LinkReach.RESTRICTED, undefined))).toBe(false);
    expect(canLinkExpire(link(undefined, undefined))).toBe(false);
  });

  it("is true for an open link without open parents", () => {
    expect(canLinkExpire(link(LinkReach.AUTHENTICATED, LinkRole.READER))).toBe(
      true,
    );
    expect(
      canLinkExpire(
        link(LinkReach.PUBLIC, LinkRole.READER, LinkReach.RESTRICTED, null),
      ),
    ).toBe(true);
  });

  it("is false when the parents open the same link", () => {
    expect(
      canLinkExpire(
        link(
          LinkReach.AUTHENTICATED,
          LinkRole.READER,
          LinkReach.AUTHENTICATED,
          LinkRole.READER,
        ),
      ),
    ).toBe(false);
  });

  it("is true when the item opens a wider reach than its parents", () => {
    expect(
      canLinkExpire(
        link(
          LinkReach.PUBLIC,
          LinkRole.READER,
          LinkReach.AUTHENTICATED,
          LinkRole.EDITOR,
        ),
      ),
    ).toBe(true);
  });

  it("is true when the item gives a higher role on the same reach", () => {
    expect(
      canLinkExpire(
        link(
          LinkReach.AUTHENTICATED,
          LinkRole.EDITOR,
          LinkReach.AUTHENTICATED,
          LinkRole.READER,
        ),
      ),
    ).toBe(true);
  });

  it("is false when the parents open a wider reach", () => {
    expect(
      canLinkExpire(
        link(
          LinkReach.AUTHENTICATED,
          LinkRole.EDITOR,
          LinkReach.PUBLIC,
          LinkRole.READER,
        ),
      ),
    ).toBe(false);
  });
});
