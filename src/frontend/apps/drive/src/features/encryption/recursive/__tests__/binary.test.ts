import { stagedFilename } from "../binary";

/** The name part, after the random folder. */
const nameOf = (title: string, filename?: string | null) =>
  stagedFilename(title, filename).split("/").slice(1).join("/");

describe("stagedFilename", () => {
  it("keeps the extension of a document titled without it", () => {
    // Created from a template: title "hey", filename "hey.odt".
    expect(nameOf("hey", "hey.odt")).toBe("hey.odt");
    // Already moved once, under a staged folder.
    expect(nameOf("hey", "3f0e0b8e-0000-4000-8000-000000000000/hey.odt")).toBe(
      "hey.odt",
    );
  });

  it("does not repeat an extension the title already has", () => {
    expect(nameOf("report.pdf", "report.pdf")).toBe("report.pdf");
    expect(nameOf("Report.PDF", "report.pdf")).toBe("Report.PDF");
  });

  it("names after the title, renamed or not", () => {
    expect(nameOf("hey - to encrypt", "hey.odt")).toBe("hey - to encrypt.odt");
  });

  it("adds nothing when the filename has no extension", () => {
    expect(nameOf("notes", "notes")).toBe("notes");
    expect(nameOf("notes")).toBe("notes");
  });
});
