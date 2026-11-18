import { describe, expect, it } from "@jest/globals";

import { resolveFrontendTheme } from "../resolveFrontendTheme";

describe("resolveFrontendTheme", () => {
  it("uses the neutral gray theme when none is configured", () => {
    expect(resolveFrontendTheme(undefined)).toBe("default");
    expect(resolveFrontendTheme(null)).toBe("default");
    expect(resolveFrontendTheme("")).toBe("default");
  });

  it("keeps a theme chosen in the configuration", () => {
    expect(resolveFrontendTheme("dsfr-light")).toBe("dsfr-light");
    expect(resolveFrontendTheme("anct-light")).toBe("anct-light");
  });
});
