// Files staged at a time: each one holds a download, the vault's work and an
// upload in flight.
const CONCURRENCY = 3;

/** A file of the job failed: the row already says why. */
export class FileStagingError extends Error {
  constructor(
    readonly itemId: string,
    readonly cause: unknown,
  ) {
    super((cause as Error)?.message ?? String(cause));
    this.name = "FileStagingError";
  }
}

/**
 * Stage `ids` CONCURRENCY at a time, and stop at the first file that fails:
 * the job can no longer be committed, so the files in flight are interrupted
 * (their transfers aborted) and none is started. Rethrows that failure, or an
 * AbortError when the user cancelled.
 */
export async function runStagingPool(
  ids: string[],
  signal: AbortSignal,
  stageOne: (id: string, signal: AbortSignal) => Promise<void>,
): Promise<void> {
  // An abort listener added after the abort never fires.
  if (signal.aborted) throw abortError();
  const interrupt = new AbortController();
  const onCancel = () => interrupt.abort();
  signal.addEventListener("abort", onCancel);
  const queue = [...ids];
  let failure: unknown = null;
  const worker = async (): Promise<void> => {
    while (queue.length > 0 && !interrupt.signal.aborted) {
      const id = queue.shift();
      if (!id) return;
      try {
        await stageOne(id, interrupt.signal);
      } catch (err) {
        if (!interrupt.signal.aborted) {
          failure = err;
          interrupt.abort();
        }
        return;
      }
    }
  };
  try {
    await Promise.all(Array.from({ length: CONCURRENCY }, () => worker()));
  } finally {
    signal.removeEventListener("abort", onCancel);
  }
  if (signal.aborted) throw abortError();
  if (failure) throw failure;
}

export function abortError(): Error {
  const e = new Error("Aborted");
  e.name = "AbortError";
  return e;
}
