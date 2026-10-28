import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { JobFileRow } from "./JobFileRow";
import { FileJobRow } from "./types";

// The distance from one row to the next, which must follow `Encryption.scss`:
// `.drive__encryption-job-row` height (40px), then the list's flex gap
// (`--c--globals--spacings--4xs`, 2px), the separator (1px) and the gap again.
// The list renders only the rows in view and pads the rest with this pitch.
const ROW_PITCH = 45;
const OVERSCAN = 6;
// `.drive__encryption-job-list` height.
const VIEWPORT_HEIGHT = 159;

/**
 * Every item of an encryption job in a fixed-height scrolling box, the failed
 * one first and scrolled into view so the reason the job stopped is visible.
 * Only the rows around the visible window are rendered, so a folder of
 * thousands of files stays fluid.
 */
export const JobFileList = ({
  rows,
  mode,
}: {
  rows: FileJobRow[];
  mode: "encrypt" | "decrypt";
}) => {
  const listRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const { ordered, hasFailed } = useMemo(() => {
    const failed = rows.filter((r) => r.state === "failed");
    return {
      ordered:
        failed.length === 0
          ? rows
          : [...failed, ...rows.filter((r) => r.state !== "failed")],
      hasFailed: failed.length > 0,
    };
  }, [rows]);

  // The failed row moved to the top: bring the top back if the user had
  // scrolled down while the job ran.
  useEffect(() => {
    if (!hasFailed || !listRef.current) return;
    listRef.current.scrollTop = 0;
    setScrollTop(0);
  }, [hasFailed]);

  const first = Math.max(0, Math.floor(scrollTop / ROW_PITCH) - OVERSCAN);
  const last = Math.min(
    ordered.length,
    Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_PITCH) + OVERSCAN,
  );

  return (
    <div
      ref={listRef}
      className="drive__encryption-job-list"
      onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
    >
      <div
        className="drive__encryption-job-list__rows"
        style={{
          paddingTop: first * ROW_PITCH,
          paddingBottom: (ordered.length - last) * ROW_PITCH,
        }}
      >
        {ordered.slice(first, last).map((row, i) => (
          <Fragment key={row.id}>
            {first + i > 0 && (
              <div
                className="drive__encryption-job-list__separator"
                aria-hidden
              />
            )}
            <JobFileRow row={row} mode={mode} />
          </Fragment>
        ))}
      </div>
    </div>
  );
};
