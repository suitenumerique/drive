import translations from "../translations.json";

type TranslationNode = { [key: string]: string | TranslationNode };

const flattenKeys = (node: TranslationNode, prefix = ""): string[] => {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "string" ? [path] : flattenKeys(value, path);
  });
};

const flattenEntries = (
  node: TranslationNode,
  prefix = ""
): [string, string][] => {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "string"
      ? ([[path, value]] as [string, string][])
      : flattenEntries(value, path);
  });
};

const languages = Object.keys(translations) as (keyof typeof translations)[];

describe("translations.json", () => {
  it("declares the same keys in every language", () => {
    const keysByLanguage = Object.fromEntries(
      languages.map((language) => [
        language,
        flattenKeys(translations[language].translation).sort(),
      ])
    );

    for (const language of languages) {
      // Compared pairwise against every other language so the failure
      // diff shows exactly which keys are missing on which side.
      for (const other of languages) {
        const missing = keysByLanguage[language].filter(
          (key) => !keysByLanguage[other].includes(key)
        );
        expect({ language: other, missing }).toEqual({
          language: other,
          missing: [],
        });
      }
    }
  });

  it.each(languages)("has no empty values in %s", (language) => {
    const empty = flattenEntries(translations[language].translation)
      .filter(([, value]) => value.trim() === "")
      .map(([key]) => key);
    expect(empty).toEqual([]);
  });
});
