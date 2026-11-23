import { ItemType } from "@/features/drivers/types";
import { isLink, openLink } from "@/features/drivers/utils";

describe("openLink", () => {
  const open = jest.fn();

  beforeEach(() => {
    open.mockReset();
    (globalThis as unknown as { window: Pick<Window, "open"> }).window = {
      open,
    };
  });

  it("opens the link in a new tab cut off from the opener", () => {
    openLink({ link_url: "https://example.com/page" });

    expect(open).toHaveBeenCalledWith(
      "https://example.com/page",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("does nothing without a link url", () => {
    openLink({ link_url: null });

    expect(open).not.toHaveBeenCalled();
  });

  it("only recognizes link items", () => {
    expect(isLink({ type: ItemType.LINK })).toBe(true);
    expect(isLink({ type: ItemType.FILE })).toBe(false);
  });
});
