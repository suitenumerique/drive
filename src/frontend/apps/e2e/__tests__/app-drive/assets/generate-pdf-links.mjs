/**
 * Generates test PDFs for e2e testing:
 *
 * 1. pdf_with_links.pdf — 3-page PDF with link annotations
 *    Page 1: title + external URI link (https://example.com) + internal GoTo link (→ page 3)
 *    Pages 2 & 3: identification text
 *
 * 2. pdf_with_js.pdf — 1-page PDF with embedded JavaScript via OpenAction
 *    Used to verify that the viewer does NOT execute embedded scripts.
 *
 * Usage:
 *   npx --package=pdf-lib node generate-pdf-links.mjs
 */

import { PDFDocument, rgb, PDFName, PDFArray, PDFDict, PDFNumber, PDFString } from "pdf-lib";
import { writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

async function generatePdfWithLinks() {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont("Helvetica");
  const PAGE_WIDTH = 595.28;
  const PAGE_HEIGHT = 841.89;

  // --- Page 1 ---
  const page1 = doc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
  page1.drawText("PDF Links Test", { x: 50, y: 750, size: 24, font, color: rgb(0, 0, 0) });
  page1.drawText("External link: https://example.com", { x: 50, y: 700, size: 14, font, color: rgb(0, 0, 1) });
  page1.drawText("Internal link: Go to page 3", { x: 50, y: 650, size: 14, font, color: rgb(0, 0, 1) });

  // --- Page 2 ---
  const page2 = doc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
  page2.drawText("Page 2", { x: 50, y: 750, size: 24, font, color: rgb(0, 0, 0) });

  // --- Page 3 ---
  const page3 = doc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
  page3.drawText("Page 3", { x: 50, y: 750, size: 24, font, color: rgb(0, 0, 0) });

  // --- Annotations (must be added at the low level) ---
  const context = doc.context;

  // External URI annotation on page 1
  const uriAction = context.obj({
    Type: "Action",
    S: "URI",
    URI: PDFString.of("https://example.com"),
  });

  const extAnnot = context.obj({
    Type: "Annot",
    Subtype: "Link",
    Rect: [45, 695, 350, 715], // around the external link text
    Border: [0, 0, 0],
    A: uriAction,
  });

  // Internal GoTo annotation on page 1 → page 3
  const page3Ref = doc.getPages()[2].ref;
  const destArray = context.obj([page3Ref, PDFName.of("Fit")]);

  const gotoAction = context.obj({
    Type: "Action",
    S: "GoTo",
    D: destArray,
  });

  const intAnnot = context.obj({
    Type: "Annot",
    Subtype: "Link",
    Rect: [45, 645, 280, 665], // around the internal link text
    Border: [0, 0, 0],
    A: gotoAction,
  });

  // Attach annotations to page 1
  const page1Dict = page1.node;
  const annotsArray = context.obj([extAnnot, intAnnot]);
  page1Dict.set(PDFName.of("Annots"), annotsArray);

  const pdfBytes = await doc.save();
  const outPath = join(__dirname, "pdf_with_links.pdf");
  writeFileSync(outPath, pdfBytes);
  console.log(`Written ${outPath} (${pdfBytes.length} bytes)`);
}

async function generatePdfWithJs() {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont("Helvetica");
  const page = doc.addPage([595.28, 841.89]);
  page.drawText("PDF with embedded JavaScript", {
    x: 50, y: 750, size: 24, font, color: rgb(0, 0, 0),
  });
  page.drawText("This PDF has an OpenAction /JavaScript entry.", {
    x: 50, y: 700, size: 14, font, color: rgb(0, 0, 0),
  });

  // Build an OpenAction that tries to execute JS when the PDF is opened.
  // A secure viewer must ignore this entirely.
  const context = doc.context;
  const jsAction = context.obj({
    Type: "Action",
    S: "JavaScript",
    JS: PDFString.of('app.alert("HACKED");'),
  });
  doc.catalog.set(PDFName.of("OpenAction"), jsAction);

  const pdfBytes = await doc.save();
  const outPath = join(__dirname, "pdf_with_js.pdf");
  writeFileSync(outPath, pdfBytes);
  console.log(`Written ${outPath} (${pdfBytes.length} bytes)`);
}

async function generatePdfWithJsLink() {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont("Helvetica");
  const PAGE_WIDTH = 595.28;
  const PAGE_HEIGHT = 841.89;

  const page = doc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
  page.drawText("PDF with javascript: link", {
    x: 50, y: 750, size: 24, font, color: rgb(0, 0, 0),
  });
  page.drawText("Click here (javascript URI)", {
    x: 50, y: 700, size: 14, font, color: rgb(0, 0, 1),
  });

  const context = doc.context;

  const uriAction = context.obj({
    Type: "Action",
    S: "URI",
    URI: PDFString.of("javascript:alert(1)"),
  });

  const annot = context.obj({
    Type: "Annot",
    Subtype: "Link",
    Rect: [45, 695, 350, 715],
    Border: [0, 0, 0],
    A: uriAction,
  });

  const pageDict = page.node;
  const annotsArray = context.obj([annot]);
  pageDict.set(PDFName.of("Annots"), annotsArray);

  const pdfBytes = await doc.save();
  const outPath = join(__dirname, "pdf_with_js_link.pdf");
  writeFileSync(outPath, pdfBytes);
  console.log(`Written ${outPath} (${pdfBytes.length} bytes)`);
}

async function main() {
  await generatePdfWithLinks();
  await generatePdfWithJs();
  await generatePdfWithJsLink();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
