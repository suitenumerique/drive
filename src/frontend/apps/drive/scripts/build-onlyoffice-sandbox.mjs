// The OnlyOffice sandbox, the page that runs OnlyOffice for encrypted documents
// on its own origin, is not a Next page: it must carry none of Drive (no
// session, no API, no vault). It is bundled on its own into
// public/onlyoffice-sandbox/, which the image serves only on the sandbox's port
// (conf/default.conf). `--watch` rebuilds it on change during development.
import { copyFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import * as esbuild from "esbuild";

const appDir = join(import.meta.dirname, "..");
const sourceDir = join(appDir, "src/features/encryption/oo-sandbox");
const outDir = join(appDir, "public/onlyoffice-sandbox");

mkdirSync(outDir, { recursive: true });
copyFileSync(join(sourceDir, "index.html"), join(outDir, "index.html"));

const options = {
  entryPoints: [join(sourceDir, "host.ts")],
  outfile: join(outDir, "host.js"),
  bundle: true,
  format: "iife",
  target: "es2020",
  minify: true,
  legalComments: "none",
  logLevel: "warning",
};

if (process.argv.includes("--watch")) {
  const context = await esbuild.context(options);
  await context.watch();
} else {
  await esbuild.build(options);
}
