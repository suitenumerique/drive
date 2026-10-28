import {
  MAX_SANDBOX_FILE_BYTES,
  exportFileName,
  parseSandboxMessage,
} from "../protocol";

const pdf = () => new TextEncoder().encode("%PDF-1.7 ...").buffer;

describe("parseSandboxMessage", () => {
  it("accepts the messages Drive acts on", () => {
    expect(parseSandboxMessage({ type: "phase", phase: "ready" })).toEqual({
      type: "phase",
      phase: "ready",
    });
    expect(
      parseSandboxMessage({
        type: "rpc",
        id: 3,
        method: "relay.sendLock",
        args: ["acquire", { guid: "x" }],
      }),
    ).toEqual({
      type: "rpc",
      id: 3,
      method: "relay.sendLock",
      args: ["acquire", { guid: "x" }],
    });
    expect(
      parseSandboxMessage({
        type: "export",
        mode: "print",
        extension: "pdf",
        title: "report.pdf",
        bytes: pdf(),
      }),
    ).toMatchObject({ type: "export", mode: "print" });
  });

  it.each([
    ["not an object", "rpc"],
    ["an unknown type", { type: "eval", code: "alert(1)" }],
    ["an unknown phase", { type: "phase", phase: "owned" }],
    [
      "a method outside the list",
      { type: "rpc", id: 1, method: "driver.deleteItem", args: [] },
    ],
    [
      "arguments a method does not take",
      { type: "rpc", id: 1, method: "relay.sendLock", args: ["steal", {}] },
    ],
    [
      "an upload too large",
      {
        type: "rpc",
        id: 1,
        method: "upload",
        args: [new ArrayBuffer(MAX_SANDBOX_FILE_BYTES + 1), "docx"],
      },
    ],
    [
      "media that is not an image",
      {
        type: "rpc",
        id: 1,
        method: "relay.queuePendingMedia",
        args: ["x.png", "data:text/html,<script>"],
      },
    ],
    [
      "a print that is not a PDF",
      {
        type: "export",
        mode: "print",
        extension: "pdf",
        title: "x.pdf",
        bytes: new TextEncoder().encode("<html>").buffer,
      },
    ],
    [
      "an export in an unknown format",
      {
        type: "export",
        mode: "download",
        extension: "exe",
        title: "x.exe",
        bytes: new ArrayBuffer(1),
      },
    ],
    [
      "a malformed peer state",
      {
        type: "reinit",
        phase: "peer-resyncing",
        peerState: { baseBin: 1, chain: [] },
      },
    ],
  ])("refuses %s", (_label, data) => {
    expect(parseSandboxMessage(data)).toBeNull();
  });
});

describe("exportFileName", () => {
  it("keeps a plain name and forces the exported extension", () => {
    expect(exportFileName("Budget 2026.xlsx", "pdf")).toBe("Budget 2026.pdf");
  });

  it("strips paths, hidden-file dots and control characters", () => {
    expect(exportFileName("../../etc/passwd", "txt")).toBe("passwd.txt");
    expect(exportFileName("..\\.bashrc", "odt")).toBe("bashrc.odt");
    expect(exportFileName("a\u0000b<c>.docx", "docx")).toBe("abc.docx");
  });

  it("falls back to a neutral name", () => {
    expect(exportFileName("...", "pdf")).toBe("document.pdf");
  });
});
