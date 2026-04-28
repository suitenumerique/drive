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
  // see in tombstone payloads (`<userId>_<ms>_<counter>`). Looking up
  // through it works uniformly across Word (CDocument), Slide
  // (CPresentation) and Calc — and avoids the per-editor walk that
  // failed for Word (whose `cSld.spTree` doesn't exist) AND the
  // refresh-everything fallback that reset CParaDrawing positions.
  const tableId = innerWindow.AscCommon?.g_oTableId;
  const lookup = tableId?.Get_ById ?? tableId?.GetById;
  if (typeof lookup !== 'function') {
    console.warn(
      '[OOEditor:auto-republish] AscCommon.g_oTableId.Get_ById not reachable — aborting nudge'
    );
    return;
  }

  // Resolve each tombstone GUID through the table. Skip entries that
  // don't expose a setRot-able xfrm (the table contains all kinds of
  // collaborative objects — paragraphs, runs, etc. — and only graphic
  // shapes carry an `spPr.xfrm`).
  const targets: Drawing[] = [];
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
    const obj = resolved as Drawing;
    const ctorName =
      (obj as { constructor?: { name?: string } }).constructor?.name;
    const ownKeys = Object.keys(obj as object).slice(0, 12);
    const wrapped = (obj.GraphicObj as Drawing | undefined) ?? null;
    const wrappedCtor = wrapped
      ? (wrapped as { constructor?: { name?: string } }).constructor?.name
      : null;
    const graphic = wrapped ?? obj;
    const hasSetRot = typeof graphic.spPr?.xfrm?.setRot === 'function';
    probe.push({
      guid,
      ctorName,
      ownKeys,
      wrappedCtor,
      hasSetRotOnGraphicObj: hasSetRot,
    });
    if (hasSetRot) targets.push(graphic);
  }

  console.log(
    '[OOEditor:auto-republish] target probe',
    JSON.stringify(
      {
        restoredGuidsRequested: restoredGuids.length,
        matchedViaTableId: targets.length,
        perGuid: probe,
      },
      null,
      2
    )
  );
  if (targets.length === 0) {
    console.warn(
      '[OOEditor:auto-republish] no shape-shaped objects resolved through g_oTableId — aborting'
    );
    return;
  }

  let mutationCount = 0;
  try {
    logicDoc.StartAction(0);
    for (const t of targets) {
      const graphic = t.GraphicObj ?? t;
      const xfrm = graphic.spPr?.xfrm;
      if (xfrm && typeof xfrm.setRot === 'function') {
        const currentRot = typeof xfrm.rot === 'number' ? xfrm.rot : 0;
        try {
          xfrm.setRot(currentRot);
          mutationCount += 1;
        } catch (e) {
          console.warn(
            '[OOEditor:auto-republish] setRot threw on drawing',
            graphic.GetId?.(),
            e
          );
        }
      }
    }
    logicDoc.FinalizeAction(false, false);
    console.log(
      '[OOEditor:auto-republish] performed',
      mutationCount,
      'setRot mutations across',
      targets.length,
      'drawing(s)'
    );
  } catch (e) {
    console.warn(
      '[OOEditor:auto-republish] direct History mutation pipeline threw',
      e
    );
  }
}
