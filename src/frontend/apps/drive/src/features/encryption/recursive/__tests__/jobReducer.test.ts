import { Item } from "@/features/drivers/types";
import { reducer } from "../useRecursiveEncryptionJob";
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
