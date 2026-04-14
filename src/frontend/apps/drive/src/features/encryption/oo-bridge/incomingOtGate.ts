/**
 * Incoming OT gate.
 *
 * Lets the checkpointing flow pause the application of remote OnlyOffice
 * changes while it captures the snapshot epoch and calls
 * `asc_nativeGetFile()`. Any remote change that arrives during the window is
 * queued and drained in order once the gate reopens.
 *
 * The epoch captured inside the gate is guaranteed to be strictly older than
 * any queued remote change — so joiners can anchor on `epochMs` and replay
 * the queued events as "post-snapshot" without duplication.
 */

type QueuedChange = () => void;

let pauseCount = 0;
const queue: QueuedChange[] = [];

export function pauseIncomingOT(): void {
  pauseCount++;
}

export function resumeIncomingOT(): void {
  if (pauseCount > 0) pauseCount--;
  if (pauseCount === 0 && queue.length > 0) {
    const drain = queue.splice(0);
    for (const fn of drain) {
      try {
        fn();
      } catch (e) {
        console.warn('[ot-gate] drain error', e);
      }
    }
  }
}

export function withIncomingOTGate(apply: QueuedChange): void {
  if (pauseCount > 0) {
    queue.push(apply);
  } else {
    apply();
  }
}
