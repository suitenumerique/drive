import i18next from "i18next";

import { DEFAULT_LANGUAGE } from "../conf";
import { i18nOptions } from "../options";

/**
 * Browsers do not agree on how to announce a language: Firefox in French sends
 * "fr" where Chrome sends "fr-FR". Both must resolve to the French we ship,
 * otherwise the components translated by the design system silently fall back
 * to English while the rest of the interface is in French.
 */
describe("language resolution", () => {
  it.each([
    ["fr", "fr-fr"],
    ["fr-FR", "fr-fr"],
    ["fr-fr", "fr-fr"],
    ["nl", "nl-nl"],
    ["en", "en-us"],
    ["en-US", "en-us"],
    ["de", DEFAULT_LANGUAGE],
  ])("resolves %s to %s", async (requested, expected) => {
    const instance = i18next.createInstance();
    await instance.init(i18nOptions);
    await instance.changeLanguage(requested);

    expect(instance.language).toBe(expected);
  });

  it("translates with the resolved language", async () => {
    const instance = i18next.createInstance();
    await instance.init(i18nOptions);
    await instance.changeLanguage("fr");

    expect(instance.t("explorer.tree.import.label")).toBe("Importer");
  });
});
