import { ItemType } from "@/features/drivers/types";
import { isLink, isWebUrl, openLink } from "@/features/drivers/utils";

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

  it("never opens a url that is not a web url", () => {
    openLink({ link_url: "javascript:alert(1)" });

    expect(open).not.toHaveBeenCalled();
  });

  it("only accepts http and https urls", () => {
    expect(isWebUrl("https://example.com")).toBe(true);
    expect(isWebUrl("HTTP://example.com")).toBe(true);
    expect(isWebUrl("javascript:alert(1)")).toBe(false);
    expect(isWebUrl("data:text/html,x")).toBe(false);
    expect(isWebUrl(null)).toBe(false);
  });

  it("only recognizes link items", () => {
    expect(isLink({ type: ItemType.LINK })).toBe(true);
    expect(isLink({ type: ItemType.FILE })).toBe(false);
  });
});
