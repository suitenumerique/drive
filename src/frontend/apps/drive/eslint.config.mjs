import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      "react-hooks/exhaustive-deps": "off",
      "@next/next/no-img-element": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },
  // The OnlyOffice sandbox is bundled on its own and runs on another origin:
  // it imports itself and the shared OnlyOffice types, nothing of Drive.
  {
    files: ["src/features/encryption/oo-sandbox/*.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              regex: "^(@/|\\.\\./(?!oo-bridge/types$))",
              message: "The OnlyOffice sandbox must not bundle Drive code.",
            },
          ],
        },
      ],
    },
  },
  // Drive reaches the sandbox through its messages only.
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/features/encryption/oo-sandbox/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              regex: "oo-sandbox/(?!protocol$)",
              message: "Only oo-sandbox/protocol is shared with Drive.",
            },
          ],
        },
      ],
    },
  },
];

export default eslintConfig;
