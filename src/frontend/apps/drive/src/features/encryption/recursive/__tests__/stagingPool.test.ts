import { runStagingPool } from "../stagingPool";

/** A file's staging that only ends when the pool interrupts it. */
const untilInterrupted = (signal: AbortSignal) =>
  new Promise<void>((_, reject) => {
    signal.addEventListener("abort", () => {
      const err = new Error("Aborted");
      err.name = "AbortError";
      reject(err);
    });
  });

describe("runStagingPool", () => {
  it("stages every file when none fails", async () => {
    const staged: string[] = [];

    await runStagingPool(
      ["a", "b", "c", "d", "e"],
      new AbortController().signal,
      async (id) => {
        staged.push(id);
      },
    );

    expect(staged.sort()).toEqual(["a", "b", "c", "d", "e"]);
  });

  it("stops at the first file that fails: the others in flight are interrupted, none is started", async () => {
    const started: string[] = [];
    const interrupted: string[] = [];
    const failure = new Error("Download failed: 404");

    const run = runStagingPool(
      ["a", "b", "c", "d", "e", "f"],
      new AbortController().signal,
      async (id, signal) => {
        started.push(id);
        if (id === "b") throw failure;
        try {
          await untilInterrupted(signal);
        } catch (err) {
          interrupted.push(id);
          throw err;
        }
      },
    );

    await expect(run).rejects.toBe(failure);
    expect(started).toEqual(["a", "b", "c"]);
    expect(interrupted.sort()).toEqual(["a", "c"]);
  });

  it("stops when the user cancels, with an AbortError", async () => {
    const controller = new AbortController();
    const started: string[] = [];

    const run = runStagingPool(
      ["a", "b", "c", "d"],
      controller.signal,
      async (id, signal) => {
        started.push(id);
        await untilInterrupted(signal);
      },
    );
    controller.abort();

    await expect(run).rejects.toMatchObject({ name: "AbortError" });
    expect(started).toEqual(["a", "b", "c"]);
  });

  it("starts nothing when the user cancelled before it began", async () => {
    const controller = new AbortController();
    controller.abort();
    const started: string[] = [];

    const run = runStagingPool(["a", "b"], controller.signal, async (id) => {
      started.push(id);
    });

    await expect(run).rejects.toMatchObject({ name: "AbortError" });
    expect(started).toEqual([]);
  });
});
