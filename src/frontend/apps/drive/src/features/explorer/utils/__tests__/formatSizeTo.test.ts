import { formatSizeTo } from "../utils";

describe("formatSizeTo", () => {
  it("returns the input as is for the B unit", () => {
    expect(formatSizeTo(1234, "B")).toBe(1234);
  });

  it("converts octets to KB", () => {
    expect(formatSizeTo(1500, "KB")).toBe(1.5);
  });

  it("converts octets to MB", () => {
    expect(formatSizeTo(1_500_000, "MB")).toBe(1.5);
  });

  it("converts octets to GB", () => {
    expect(formatSizeTo(2_000_000_000, "GB")).toBe(2);
  });

  it("converts octets to TB", () => {
    expect(formatSizeTo(1_000_000_000_000, "TB")).toBe(1);
  });

  it("converts octets to PB", () => {
    expect(formatSizeTo(2_500_000_000_000_000, "PB")).toBe(2.5);
  });

  it("returns fractional values when the size is smaller than the unit", () => {
    expect(formatSizeTo(500, "KB")).toBe(0.5);
  });

  it("returns 0 for an empty size", () => {
    expect(formatSizeTo(0, "GB")).toBe(0);
  });
});
