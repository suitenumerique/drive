import { formatSize } from "../utils";

// Same cases as the backend format_size tests, keep them in sync
describe("formatSize", () => {
  it.each([
    [0, "0.00 B"],
    [999, "999 B"],
    [1000, "1.00 KB"],
    [9_994, "9.99 KB"],
    [10_000, "10.0 KB"],
    [99_940, "99.9 KB"],
    [100_500, "101 KB"],
    [999_999, "1000 KB"],
    [3_631_743_364, "3.63 GB"],
    [15_000_000_000, "15.0 GB"],
    [155_800_000, "156 MB"],
    [10 ** 18, "1000 PB"],
  ])("formats %d bytes as %s", (size, expected) => {
    expect(formatSize(size)).toBe(expected);
  });

  it("translates the unit", () => {
    expect(formatSize(1500, (key) => `t:${key}`)).toBe(
      "1.50 t:explorer.grid.size_units.KB",
    );
  });
});
