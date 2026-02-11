import { useEffect, useMemo, useState } from "react";
import type { TimeBound } from "./timeBounds";

export type TimeBoundedPhase = "loading" | "still_working" | "failed";

export const useTimeBoundedPhase = (
  isActive: boolean,
  bounds: TimeBound
): TimeBoundedPhase => {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [phase, setPhase] = useState<TimeBoundedPhase>("loading");

  const stillWorkingMs = useMemo(
    () => Math.max(0, bounds.still_working_ms),
    [bounds.still_working_ms]
  );
  const failMs = useMemo(() => Math.max(0, bounds.fail_ms), [bounds.fail_ms]);

  useEffect(() => {
    if (!isActive) {
      setStartedAt(null);
      setPhase("loading");
      return;
    }
    setStartedAt(Date.now());
    setPhase("loading");
  }, [isActive]);

  useEffect(() => {
    if (!isActive || startedAt === null) {
      return;
    }

    const stillWorkingTimer = globalThis.setTimeout(() => {
      setPhase("still_working");
    }, stillWorkingMs);

    const failTimer = globalThis.setTimeout(() => {
      setPhase("failed");
    }, failMs);

    return () => {
      globalThis.clearTimeout(stillWorkingTimer);
      globalThis.clearTimeout(failTimer);
    };
  }, [isActive, startedAt, stillWorkingMs, failMs]);

  return phase;
};
