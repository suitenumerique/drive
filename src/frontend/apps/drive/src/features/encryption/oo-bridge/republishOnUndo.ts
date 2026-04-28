// ---------------------------------------------------------------------------
// Shape-restoration republish helpers (experimental).
//
// The OO undo of a shape delete emits "tombstone" deltas (~120 bytes,
// referencing the shape's GUID) that assume the receiver's local history
// holds the shape's full data. A peer that joined post-deletion never
// recorded the inverse data, so the apply silently no-ops and the shape
// stays invisible. Workaround: detect those tombstones on the outbound
// pipeline, then mutate every restored shape's transform inside a
// `StartAction` / `FinalizeAction` bracket — OO emits transform deltas
// receivers can render directly. No visible motion on the sender's screen.
//
// Detection is heuristic: parse each outgoing change's `<byteLen>;<base64>`
// payload, decode the base64, scan the bytes for a UTF-16-LE substring
// matching the OO shape GUID format `<userId>_<timestamp_ms>_<counter>`,
// and only republish when at least one such GUID appears AND every change
// in the envelope is small (< AUTO_REPUBLISH_BYTE_THRESHOLD bytes — i.e.
// none of them carry full shape data already).
// ---------------------------------------------------------------------------

const AUTO_REPUBLISH_BYTE_THRESHOLD = 250;
const SHAPE_GUID_PATTERN =
  /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}_\d{10,}_\d+/g;

/**
 * Unwrap an OO change field. OO stores each `change` as a JSON-stringified
 * `"<byteLen>;<base64>"` value (note the wrapping quotes), not a bare
 * `<byteLen>;<base64>`. Returns the raw inner string with the quotes
 * removed; falls back to the input if it isn't quoted.
 */
function unwrapChangeString(rawChange: string): string {
  if (
    rawChange.length >= 2 &&
    rawChange.startsWith('"') &&
    rawChange.endsWith('"')
  ) {
    try {
      const parsed = JSON.parse(rawChange);
      if (typeof parsed === 'string') return parsed;
    } catch {
      /* fall through */
    }
  }
  return rawChange;
}

/**
 * Decode an OO `<byteLen>;<base64>` change payload as UTF-16-LE text. The
 * binary stream interleaves UTF-16 strings with non-text metadata; we
 * decode the lot indiscriminately so the GUID regex can find the embedded
 * GUID regardless of where it sits within the payload.
 */
function decodeChangeAsUtf16LE(rawChange: string): string {
  const inner = unwrapChangeString(rawChange);
  const semi = inner.indexOf(';');
  if (semi < 0) return '';
  const b64 = inner.slice(semi + 1);
  let bin: string;
  try {
    bin = atob(b64);
  } catch {
    return '';
  }
  let out = '';
  for (let i = 0; i + 1 < bin.length; i += 2) {
    out += String.fromCharCode(
      bin.charCodeAt(i) | (bin.charCodeAt(i + 1) << 8)
    );
  }
  return out;
}

/**
 * Inspect an outbound saveChanges envelope. Returns:
 *  - `guids`: every shape GUID matched in any "small" change payload
 *    (= the tombstones we want to republish).
 *  - `hasFatShapeChange`: true when any change is large enough to plausibly
 *    carry a full shape add — in that case republishing would be noise
 *    and we'll skip even if a small tombstone is also present.
 *  - `sizes`: per-change byte length (for diagnostics).
 *  - `totalBytes`: sum of byte lengths.
 */
export function inspectOutboundForRepublish(
  message: Record<string, unknown>
): {
  guids: string[];
  hasFatShapeChange: boolean;
  sizes: number[];
  totalBytes: number;
} {
  const changes = (message as { changes?: unknown }).changes;
  if (!Array.isArray(changes)) {
    return {
      guids: [],
      hasFatShapeChange: false,
      sizes: [],
      totalBytes: 0,
    };
  }
  const guids = new Set<string>();
  let hasFatShapeChange = false;
  const sizes: number[] = [];
  let totalBytes = 0;
  for (const c of changes) {
    const raw = (c as { change?: string }).change ?? '';
    const inner = unwrapChangeString(raw);
    const semi = inner.indexOf(';');
    const parsedLen =
      semi > 0 ? parseInt(inner.slice(0, semi), 10) : NaN;
    const byteLen = Number.isFinite(parsedLen) ? parsedLen : inner.length;
    sizes.push(byteLen);
    totalBytes += byteLen;
    const decoded = decodeChangeAsUtf16LE(raw);
    // Use matchAll — a single tombstone may reference several object
    // GUIDs (e.g. wrapper + graphic + run). Collect them all so the
    // downstream lookup has every candidate.
    const matches = [...decoded.matchAll(SHAPE_GUID_PATTERN)];
    if (matches.length > 0) {
      // Treat large GUID-bearing changes as full-data adds (e.g. a
      // shape paste / republish) — record the size flag so the caller
      // can decide not to fire a redundant republish.
      if (byteLen > AUTO_REPUBLISH_BYTE_THRESHOLD) {
        hasFatShapeChange = true;
      } else {
        for (const m of matches) guids.add(m[0]);
      }
    }
  }
  return { guids: Array.from(guids), hasFatShapeChange, sizes, totalBytes };
}

/**
 * For every shape matched by `restoredGuids` in the active slide, call
 * `xfrm.setRot(currentRot)` once inside a `StartAction` /
 * `FinalizeAction` bracket. `CXfrm.prototype.setRot` unconditionally
 * pushes a `CChangesDrawingsDouble(this, historyitem_Xfrm_SetRot, oldVal, newVal)`
 * to History — this single same-value call is the test variant; if
 * receivers don't refresh, swap to a `setRot(curr+ε); setRot(curr)`
 * pair instead.
 */
/**
 * Tracks the timestamp of the most recent `editor.Undo()` call so the
 * republish heuristic can distinguish a tombstone undo from a regular
 * forward delete (whose payload looks identical from the wire).
 *
 * Why a flag instead of querying OO state: in fast-collaborative mode
 * Ctrl+Z goes through `CCollaborativeHistory.UndoOwnPoint`, which
 * creates a NEW local history point with the inverse changes rather
 * than popping from undo and pushing to redo. As a result
 * `History.Can_Redo()` returns false even right after a Ctrl+Z, so
 * that signal is unusable. The API-level `editor.Undo` method is
 * still the single entry point for both Ctrl+Z and the toolbar undo,
 * regardless of collab mode.
 */
let lastUndoAt = 0;
const HOOK_FLAG = '__driveUndoFlagHookInstalled';

/**
 * Patch every `Undo` method in OO's call chain so we stamp
 * `lastUndoAt` regardless of which entry point Ctrl+Z hit:
 *  - the editor API (`asc_docs_api.prototype.Undo` — `editor.Undo`)
 *  - the collaborative editing instance
 *    (`CCollaborativeEditingBase.prototype.Undo` —
 *    `AscCommon.CollaborativeEditing.Undo`)
 *
 * Two independent prototypes are patched so the timestamp is set
 * either way. Idempotent via per-prototype flag.
 */
function patchUndoOnPrototype(
  proto: Record<string, unknown> | null | undefined,
  label: string,
): boolean {
  if (!proto) return false;
  if ((proto as { [k: string]: unknown })[HOOK_FLAG]) return true;
  const original = proto['Undo'];
  if (typeof original !== 'function') return false;
  proto['Undo'] = function patched(this: unknown, ...args: unknown[]) {
    lastUndoAt = Date.now();
    console.log('[republishOnUndo] Undo fired via', label);
    return (original as (...a: unknown[]) => unknown).apply(this, args);
  };
  (proto as { [k: string]: unknown })[HOOK_FLAG] = true;
  console.log('[republishOnUndo] Undo flag-hook installed on', label);
  return true;
}

export function installUndoFlagHook(): void {
  const ooIframe = document.querySelector(
    'iframe[name="frameEditor"]'
  ) as HTMLIFrameElement | null;
  const innerWindow = ooIframe?.contentWindow as
    | (Window & {
        editor?: unknown;
        editorCell?: unknown;
        AscCommon?: { CollaborativeEditing?: unknown };
      })
    | undefined;
  if (!innerWindow) return;
  const innerEditor = innerWindow.editor || innerWindow.editorCell;
  if (innerEditor && typeof innerEditor === 'object') {
    patchUndoOnPrototype(
      Object.getPrototypeOf(innerEditor) as Record<string, unknown>,
      'asc_docs_api',
    );
  }
  const collab = innerWindow.AscCommon?.CollaborativeEditing;
  if (collab && typeof collab === 'object') {
    patchUndoOnPrototype(
      Object.getPrototypeOf(collab) as Record<string, unknown>,
      'CCollaborativeEditingBase',
    );
  }
}

/**
 * True if `editor.Undo()` was invoked within the last `windowMs`. Used
 * to gate the republish so it never fires after a forward delete —
 * only after an actual Ctrl+Z (or toolbar undo).
 */
export function undoFiredRecently(windowMs: number = 1000): boolean {
  return Date.now() - lastUndoAt < windowMs;
}

export function dispatchRepublishNudge(restoredGuids: string[]): void {
  const ooIframe = document.querySelector(
    'iframe[name="frameEditor"]'
  ) as HTMLIFrameElement | null;
  const innerWindow = ooIframe?.contentWindow as
    | (Window & {
        editor?: { WordControl?: { m_oLogicDocument?: unknown } };
        editorCell?: { WordControl?: { m_oLogicDocument?: unknown } };
        AscCommon?: {
          g_oTableId?: {
            Get_ById?: (id: string) => unknown;
            GetById?: (id: string) => unknown;
          };
        };
      })
    | undefined;
  if (!innerWindow) {
    console.warn('[OOEditor:auto-republish] inner window not found');
    return;
  }
  const innerEditor = innerWindow.editor || innerWindow.editorCell;
  type Xfrm = {
    rot?: number;
    setRot?: (val: number) => void;
  };
  type Drawing = {
    GetId?: () => string;
    spPr?: { xfrm?: Xfrm };
    spTree?: unknown[];
    /**
     * Word stores drawings as `CParaDrawing` wrappers — the actual
     * shape (with `spPr.xfrm`) lives one level down.
     */
    GraphicObj?: {
      GetId?: () => string;
      spPr?: { xfrm?: Xfrm };
      spTree?: unknown[];
    };
  };
  type LogicDocLike = {
    StartAction?: (nDescription: number, additional?: unknown) => void;
    FinalizeAction?: (
      isCheckEmptyAction?: boolean,
      isCheckLockedAction?: boolean,
      additional?: unknown
    ) => void;
    /** Slide context (CPresentation). */
    Slides?: Array<{ cSld?: { spTree?: unknown } }>;
    CurPage?: number;
    /** Word context (CDocument inherits from CDocumentContentBase). */
    GetAllDrawingObjects?: (arr?: Drawing[]) => Drawing[];
  };
  const logicDoc = (innerEditor?.WordControl?.m_oLogicDocument ??
    null) as LogicDocLike | null;
  if (!logicDoc?.StartAction || !logicDoc?.FinalizeAction) {
    console.warn(
      '[OOEditor:auto-republish] StartAction/FinalizeAction not reachable on logic document; aborting nudge'
    );
    return;
  }

  // OO maintains a global, single-keyed-by-wire-GUID object table at
  // `AscCommon.g_oTableId` (a `CTableId` instance). Every collaborative
  // object — drawings, paragraphs, runs, etc. — is registered there at
  // construction time, with its `Id` set to the wire-format GUID we
  // see in tombstone payloads (`<userId>_<ms>_<counter>`).
  const tableId = innerWindow.AscCommon?.g_oTableId;
  const lookup = tableId?.Get_ById ?? tableId?.GetById;
  if (typeof lookup !== 'function') {
    console.warn(
      '[OOEditor:auto-republish] AscCommon.g_oTableId.Get_ById not reachable — aborting nudge'
    );
    return;
  }

  // Refresh strategy:
  //   - Slide / Calc shape (registered directly in g_oTableId, no
  //     wrapper): refresh via `spPr.xfrm.setRot(curr)`. Position is
  //     already on the same xfrm so the receiver renders correctly.
  //   - Word ParaDrawing wrapper: refresh via the inner GraphicObj's
  //     `setRot` AND re-broadcast the wrapper's position info
  //     (`Set_PositionH`, `Set_PositionV`, `setSimplePos`). The inner
  //     xfrm setRot alone landed the shape at top-left on receivers
  //     because the wrapper's PositionH/V on user 2's side had been
  //     reset to defaults; refreshing those too pushes the actual
  //     anchor values over the wire.
  type ParaDrawingLike = {
    PositionH?: {
      RelativeFrom?: number;
      Align?: boolean;
      Value?: number;
      Percent?: boolean;
    };
    PositionV?: {
      RelativeFrom?: number;
      Align?: boolean;
      Value?: number;
      Percent?: boolean;
    };
    SimplePos?: { Use?: boolean; X?: number; Y?: number };
    Set_PositionH?: (
      relativeFrom: number,
      align: boolean,
      value: number,
      percent: boolean
    ) => void;
    Set_PositionV?: (
      relativeFrom: number,
      align: boolean,
      value: number,
      percent: boolean
    ) => void;
    setSimplePos?: (use: boolean, x: number, y: number) => void;
  };
  type Refresh = {
    xfrm: { rot?: number; setRot?: (v: number) => void };
    /** Word-only — present when the resolved object is a ParaDrawing wrapper. */
    paraDrawing?: ParaDrawingLike;
  };
  const refreshes: Refresh[] = [];
  const probe: Array<Record<string, unknown>> = [];
  for (const guid of restoredGuids) {
    let resolved: unknown;
    try {
      resolved = lookup.call(tableId, guid);
    } catch (e) {
      console.warn(
        '[OOEditor:auto-republish] g_oTableId.Get_ById threw for',
        guid,
        e
      );
      probe.push({ guid, error: String(e) });
      continue;
    }
    if (!resolved) {
      probe.push({ guid, resolved: 'null' });
      continue;
    }
    const obj = resolved as Drawing & ParaDrawingLike;
    const ctorName =
      (obj as { constructor?: { name?: string } }).constructor?.name;
    const xfrm = obj.spPr?.xfrm ?? obj.GraphicObj?.spPr?.xfrm;
    if (xfrm && typeof xfrm.setRot === 'function') {
      // ParaDrawing-shape detected when the wrapper-level position
      // setters exist on the resolved object.
      const isParaDrawing =
        typeof obj.Set_PositionH === 'function' &&
        typeof obj.Set_PositionV === 'function' &&
        typeof obj.setSimplePos === 'function';
      probe.push({
        guid,
        ctorName,
        refresh: isParaDrawing ? 'xfrm.setRot+position' : 'xfrm.setRot',
      });
      refreshes.push({
        xfrm,
        paraDrawing: isParaDrawing ? obj : undefined,
      });
    } else {
      probe.push({ guid, ctorName, refresh: 'none' });
    }
  }

  console.log(
    '[OOEditor:auto-republish] target probe',
    JSON.stringify(
      {
        restoredGuidsRequested: restoredGuids.length,
        refreshes: refreshes.length,
        perGuid: probe,
      },
      null,
      2
    )
  );
  if (refreshes.length === 0) {
    console.warn(
      '[OOEditor:auto-republish] no refreshable objects resolved — aborting'
    );
    return;
  }

  let mutationCount = 0;
  try {
    logicDoc.StartAction(0);
    const ROT_EPSILON = 1e-7;
    const POS_EPSILON = 1; // 1 EMU ≈ 1/914400 inch — invisible
    for (const r of refreshes) {
      try {
        // setRot ε-pair on the inner xfrm (always — slides need this,
        // Word also needs the inner refresh).
        const cur = typeof r.xfrm.rot === 'number' ? r.xfrm.rot : 0;
        r.xfrm.setRot!(cur + ROT_EPSILON);
        r.xfrm.setRot!(cur);
        mutationCount += 2;

        // Word-only: also re-broadcast wrapper position. Same ε-pair
        // pattern so the broadcast pipeline doesn't filter empty
        // changes.
        const pd = r.paraDrawing;
        if (pd) {
          // PositionH
          if (pd.PositionH && typeof pd.Set_PositionH === 'function') {
            const ph = pd.PositionH;
            const rf = ph.RelativeFrom ?? 0;
            const al = ph.Align ?? false;
            const v = typeof ph.Value === 'number' ? ph.Value : 0;
            const pc = ph.Percent ?? false;
            pd.Set_PositionH(rf, al, v + POS_EPSILON, pc);
            pd.Set_PositionH(rf, al, v, pc);
            mutationCount += 2;
          }
          // PositionV
          if (pd.PositionV && typeof pd.Set_PositionV === 'function') {
            const pv = pd.PositionV;
            const rf = pv.RelativeFrom ?? 0;
            const al = pv.Align ?? false;
            const v = typeof pv.Value === 'number' ? pv.Value : 0;
            const pc = pv.Percent ?? false;
            pd.Set_PositionV(rf, al, v + POS_EPSILON, pc);
            pd.Set_PositionV(rf, al, v, pc);
            mutationCount += 2;
          }
          // SimplePos
          if (pd.SimplePos && typeof pd.setSimplePos === 'function') {
            const sp = pd.SimplePos;
            const use = sp.Use ?? false;
            const x = typeof sp.X === 'number' ? sp.X : 0;
            const y = typeof sp.Y === 'number' ? sp.Y : 0;
            pd.setSimplePos(use, x + POS_EPSILON, y + POS_EPSILON);
            pd.setSimplePos(use, x, y);
            mutationCount += 2;
          }
        }
      } catch (e) {
        console.warn(
          '[OOEditor:auto-republish] mutation threw',
          e
        );
      }
    }
    logicDoc.FinalizeAction(false, false);
    // NOTE on history hygiene: ideally we'd `History.RemoveLastPoint()`
    // here so our virtual ε-pair doesn't bloat the user's undo stack.
    // Empirically that kills the broadcast even with a setTimeout
    // delay — the wire flush isn't bounded by a fixed interval. For
    // now we accept the extra history point; the upstream Can_Redo /
    // Undo-fired gates already prevent the heuristic from firing on
    // forward actions, so the only pollution is right after a real
    // undo.
    console.log(
      '[OOEditor:auto-republish] performed',
      mutationCount,
      'mutations across',
      refreshes.length,
      'object(s)'
    );
  } catch (e) {
    console.warn(
      '[OOEditor:auto-republish] direct History mutation pipeline threw',
      e
    );
  }
}
