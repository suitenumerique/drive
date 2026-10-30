import { describe, expect, it } from "@jest/globals";

import { formatPageTitle } from "../pageTitle";

describe("formatPageTitle", () => {
  it("identifies the current page and the application", () => {
    expect(formatPageTitle("Mes fichiers", "Fichiers")).toBe(
      "Mes fichiers | Fichiers",
    );
  });

  it("keeps the application name when the page name is empty", () => {
    expect(formatPageTitle("   ", "Fichiers")).toBe("Fichiers");
  });
});
