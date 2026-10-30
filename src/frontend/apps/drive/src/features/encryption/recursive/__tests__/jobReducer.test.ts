import { Item } from "@/features/drivers/types";
import { APIError } from "@/features/api/APIError";
import { reducer, refusedFiles } from "../useRecursiveEncryptionJob";
import { FileJobRow, FileJobState } from "../types";

const row = (id: string, state: FileJobState): FileJobRow => ({
  id,
  title: id,
  path: "",
  item: { id } as Item,
  state,
});

const withRows = (rows: FileJobRow[]) =>
  reducer({ rows: [], rowIndexById: {} } as never, { type: "SET_ROWS", rows });

const states = (state: ReturnType<typeof reducer>) =>
  Object.fromEntries(state.rows.map((r) => [r.id, [r.state, r.error]]));

describe("a failed operation", () => {
  it("fails the rows the server names and takes the check mark off the others", () => {
    const state = reducer(
      withRows([
        row("held", "staged"),
        row("other", "staged"),
        row("skipped", "skipped"),
      ]),
      {
        type: "FAIL",
        error: "A document is still being saved by its editor.",
        rowErrors: { held: "still being saved by its editor" },
      },
    );

    expect(states(state)).toEqual({
      held: ["failed", "still being saved by its editor"],
      // Nothing was saved: back to pending, done again by a retry.
      other: ["pending", undefined],
      skipped: ["skipped", undefined],
    });
  });

  it("fails a row still running with the operation's error", () => {
    const state = reducer(withRows([row("a", "running"), row("b", "staged")]), {
      type: "FAIL",
      error: "Server error",
    });

    expect(states(state)).toEqual({
      a: ["failed", "Server error"],
      b: ["pending", undefined],
    });
  });
});

describe("a refused commit", () => {
  it("is retried with the files the server names, read again", () => {
    expect(
      refusedFiles(new APIError(409, { code: "item_changed", items: ["a"] })),
    ).toEqual({ code: "item_changed", ids: ["a"] });
    expect(
      refusedFiles(
        new APIError(409, { code: "item_being_edited", items: ["b"] }),
      ),
    ).toEqual({ code: "item_being_edited", ids: ["b"] });
  });

  it("is not retried for any other cause, nor without files to read again", () => {
    expect(
      refusedFiles(
        new APIError(409, { code: "subtree_mutated", items: ["a"] }),
      ),
    ).toBeNull();
    expect(
      refusedFiles(new APIError(409, { code: "item_changed", items: [] })),
    ).toBeNull();
    expect(refusedFiles(new Error("network"))).toBeNull();
  });
});

describe("a commit retried for refused files", () => {
  it("takes their check mark off and says why until the job ends", () => {
    const retrying = reducer(
      withRows([row("held", "staged"), row("other", "staged")]),
      { type: "RETRY_REFUSED", ids: ["held"], notice: "Still being saved" },
    );

    expect(retrying.phase).toBe("staging");
    expect(retrying.retryNotice).toBe("Still being saved");
    expect(states(retrying)).toEqual({
      held: ["pending", undefined],
      other: ["staged", undefined],
    });
    expect(
      reducer(retrying, { type: "CLEAR_RETRY_NOTICE" }).retryNotice,
    ).toBeNull();
    expect(
      reducer(retrying, { type: "FAIL", error: "Server error" }).retryNotice,
    ).toBeNull();
  });
});
