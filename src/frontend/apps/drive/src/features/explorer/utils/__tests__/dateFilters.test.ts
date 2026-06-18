import { presetRange, toISODate } from "../dateFilters";

describe("presetRange", () => {
  // 2026-05-29 in local time (month is 0-indexed).
  const today = new Date(2026, 4, 29);

  it("returns the current day for the today preset", () => {
    expect(presetRange("today", today)).toEqual({
      updated_at_after: "2026-05-29",
      updated_at_before: "2026-05-29",
    });
  });

  it("spans the last 7 days, today included", () => {
    expect(presetRange("last_7_days", today)).toEqual({
      updated_at_after: "2026-05-23",
      updated_at_before: "2026-05-29",
    });
  });

  it("spans the last 30 days, today included", () => {
    expect(presetRange("last_30_days", today)).toEqual({
      updated_at_after: "2026-04-30",
      updated_at_before: "2026-05-29",
    });
  });

  it("spans from the first day of the year", () => {
    expect(presetRange("this_year", today)).toEqual({
      updated_at_after: "2026-01-01",
      updated_at_before: "2026-05-29",
    });
  });

  it("caps at one year ago for the more than a year preset", () => {
    expect(presetRange("more_than_a_year", today)).toEqual({
      updated_at_before: "2025-05-29",
    });
  });
});

describe("toISODate", () => {
  it("formats a local date as YYYY-MM-DD", () => {
    expect(toISODate(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
