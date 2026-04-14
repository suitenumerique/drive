/**
 * x2t WASM format converter wrapper.
 *
 * Converts between office formats (docx, xlsx, pptx, odt, ods, odp)
 * and OnlyOffice's internal .bin format. All conversion happens in the
 * browser via WebAssembly — no server involved.
 */

import { EXTENSION_TO_X2T_TYPE } from './types';

// x2t WASM module interface (Emscripten)
interface X2TModule {
  FS: {
    mkdir(path: string): void;
    writeFile(path: string, data: Uint8Array | string): void;
    readFile(path: string, opts?: { encoding: string }): Uint8Array;
    readdir(path: string): string[];
    unlink(path: string): void;
    rmdir?(path: string): void;
  };
  ccall(
    ident: string,
    returnType: string,
    argTypes: string[],
    args: unknown[]
  ): unknown;
  onRuntimeInitialized?: () => void;
}

// Store on window to survive HMR module reloads
const getWindow = (): any => (typeof window !== 'undefined' ? window : {});
const getX2TModule = (): X2TModule | null => getWindow().__x2tModule ?? null;
const setX2TModule = (m: X2TModule) => { getWindow().__x2tModule = m; };
const getX2TReady = (): Promise<X2TModule> | null => getWindow().__x2tReady ?? null;
const setX2TReady = (p: Promise<X2TModule>) => { getWindow().__x2tReady = p; };

/**
 * Get or initialize the x2t WASM module.
 * The WASM is loaded from /onlyoffice/x2t/x2t.js (static asset).
 */
function getX2T(): Promise<X2TModule> {
  // If already resolved, return immediately
  const cached = getX2TModule();
  if (cached) return Promise.resolve(cached);

  // If already loading, return the existing promise
  const pending = getX2TReady();
  if (pending) return pending;

  // Check if Module was loaded by a previous render
  const existing = (window as any).Module;
  if (existing?.FS?.readdir) {
    setX2TModule(existing as X2TModule);
    return Promise.resolve(existing as X2TModule);
  }

  const promise = new Promise<X2TModule>((resolve, reject) => {
    const x2tUrl = new URL('/onlyoffice/x2t/x2t.js', window.location.origin).href;

    if (document.querySelector(`script[src="${x2tUrl}"]`)) {
      const poll = setInterval(() => {
        const mod = (window as any).Module;
        if (mod?.FS?.readdir) {
          clearInterval(poll);
          try { mod.FS.mkdir('/working'); } catch {}
          try { mod.FS.mkdir('/working/media'); } catch {}
          try { mod.FS.mkdir('/working/fonts'); } catch {}
          try { mod.FS.mkdir('/working/themes'); } catch {}
          setX2TModule(mod);
          resolve(mod);
        }
      }, 200);
      setTimeout(() => { clearInterval(poll); reject(new Error('x2t timeout')); }, 30000);
      return;
    }

    (window as any).Module = {
      locateFile: (path: string) =>
        new URL(`/onlyoffice/x2t/${path}`, window.location.origin).href,
      onRuntimeInitialized: () => {
        const mod = (window as any).Module as X2TModule;
        try { mod.FS.mkdir('/working'); } catch {}
        try { mod.FS.mkdir('/working/media'); } catch {}
        try { mod.FS.mkdir('/working/fonts'); } catch {}
        try { mod.FS.mkdir('/working/themes'); } catch {}
        setX2TModule(mod);
        resolve(mod);
      },
    };

    const script = document.createElement('script');
    script.src = x2tUrl;
    script.onerror = () => reject(new Error('Failed to load x2t WASM'));
    document.head.appendChild(script);
  });

  setX2TReady(promise);
  return promise;
}

/**
 * Get file extension from filename.
 */
function getExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop()!.toLowerCase() : '';
}

/**
 * Sanitize filename for x2t (remove special chars).
 */
function sanitize(input: string): string {
  const parts = input.split('.');
  const ext = parts.pop() || 'bin';
  let name = parts.join('') || 'file';
  name = name
    .replace(/[\/\?<>\\:\*\|"]/g, '')
    .replace(/[\x00-\x1f\x80-\x9f]/g, '')
    .replace(/^\.+$/, '')
    .replace(/[&'%!"{}[\]]/g, '');
  return (name || 'file').slice(0, 255) + '.' + ext;
}

/**
 * Run x2t conversion on the WASM module.
 */
// Basic Latin font set used by the x2t PDF writer. These are the same
// metrically-compatible substitutes OnlyOffice ships for Arial / Calibri /
// Times New Roman / Courier New, which is what virtually every Office doc
// references. Loaded lazily on first PDF conversion since they're ~3 MB.
const PDF_FONT_FILES = [
  'Arimo-Regular.ttf',
  'Arimo-Bold.ttf',
  'Arimo-Italic.ttf',
  'Arimo-BoldItalic.ttf',
  'Carlito-Regular.ttf',
  'Carlito-Bold.ttf',
  'Carlito-Italic.ttf',
  'Carlito-BoldItalic.ttf',
  'Tinos-Regular.ttf',
  'Tinos-Bold.ttf',
  'Tinos-Italic.ttf',
  'Tinos-BoldItalic.ttf',
  'Cousine-Regular.ttf',
  'Cousine-Bold.ttf',
  'Cousine-Italic.ttf',
  'Cousine-BoldItalic.ttf',
];

let fontsLoaded = false;
async function ensureFontsLoaded(x2t: X2TModule): Promise<void> {
  if (fontsLoaded) return;
  const fontsBase = '/onlyoffice/v9/fonts/fonts/';
  await Promise.all(
    PDF_FONT_FILES.map(async name => {
      try {
        const resp = await fetch(fontsBase + name);
        if (!resp.ok) return;
        const buf = new Uint8Array(await resp.arrayBuffer());
        x2t.FS.writeFile('/working/fonts/' + name, buf);
      } catch {
        /* font missing — skip */
      }
    }),
  );
  // Load the CMap database that x2t's PDF writer needs to encode glyphs.
  try {
    x2t.FS.mkdir('/working/cmaps');
  } catch {
    /* exists */
  }
  try {
    const resp = await fetch(
      '/onlyoffice/v9/sdkjs/pdf/src/engine/cmap.bin',
    );
    if (resp.ok) {
      const buf = new Uint8Array(await resp.arrayBuffer());
      x2t.FS.writeFile('/working/cmaps/cmap.bin', buf);
    }
  } catch {
    /* cmap missing */
  }
  fontsLoaded = true;
}

// Cached state in /working that should NEVER be cleared between conversions:
// fonts, the CMap database, the themes dir layout. Everything else is
// per-document scratch (the input bin, intermediate files, extracted media)
// and must be wiped before each run so we never leak across docs or grow
// the WASM heap.
const WORKING_KEEP = new Set(['.', '..', 'fonts', 'cmaps', 'themes']);
function clearWorkingDir(x2t: X2TModule): void {
  try {
    for (const entry of x2t.FS.readdir('/working')) {
      if (WORKING_KEEP.has(entry)) continue;
      try {
        x2t.FS.unlink('/working/' + entry);
      } catch {
        /* might be a dir we don't recurse into */
      }
    }
  } catch {
    /* /working not yet created */
  }
  // /working/media/ contents are scratch; wipe per run.
  try {
    for (const entry of x2t.FS.readdir('/working/media')) {
      if (entry === '.' || entry === '..') continue;
      try {
        x2t.FS.unlink('/working/media/' + entry);
      } catch {
        /* skip */
      }
    }
  } catch {
    /* media dir not yet created */
  }
}

// Emscripten's FS.readFile returns Uint8Array<ArrayBufferLike> (the backing
// buffer might be a SharedArrayBuffer on some builds). Copy into a fresh
// ArrayBuffer so the rest of the pipeline can use strict ArrayBuffer types
// (Blob, the upload callback, etc.).
function toStrictUint8Array(src: Uint8Array): Uint8Array<ArrayBuffer> {
  const out = new Uint8Array(new ArrayBuffer(src.byteLength));
  out.set(src);
  return out as Uint8Array<ArrayBuffer>;
}

function runConversion(
  x2t: X2TModule,
  inputName: string,
  inputData: Uint8Array,
  outputFormat: string
): Uint8Array<ArrayBuffer> | null {
  x2t.FS.writeFile('/working/' + inputName, inputData);

  const outputPath = `/working/${inputName}.${outputFormat}`;
  // For PDF output, x2t's writer needs extra params the default conversion
  // path doesn't: an explicit format code, the font directory, and the CMap
  // database. Adding these only for the PDF step so other paths stay
  // untouched.
  const pdfExtras =
    outputFormat === 'pdf'
      ? [
          '  <m_nFormatTo>513</m_nFormatTo>',
          '  <m_sFontDir>/working/fonts/</m_sFontDir>',
          '  <m_sCmapDir>/working/cmaps/</m_sCmapDir>',
        ]
      : [];
  const params = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<TaskQueueDataConvert',
    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
    '  xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
    `  <m_sFileFrom>/working/${inputName}</m_sFileFrom>`,
    `  <m_sFileTo>${outputPath}</m_sFileTo>`,
    '  <m_sThemeDir>/working/themes</m_sThemeDir>',
    '  <m_bIsNoBase64>false</m_bIsNoBase64>',
    ...pdfExtras,
    '</TaskQueueDataConvert>',
  ].join('\n');

  x2t.FS.writeFile('/working/params.xml', params);

  if (outputFormat === 'pdf') {
    try {
      const fontsList = x2t.FS.readdir('/working/fonts');
      console.log(
        '[x2t] /working/fonts contents before PDF conversion:',
        fontsList,
      );
    } catch (e) {
      console.warn('[x2t] could not list /working/fonts:', e);
    }
    console.log('[x2t] params.xml:\n' + params);
  }

  let rc: unknown = -1;
  try {
    rc = x2t.ccall('main1', 'number', ['string'], ['/working/params.xml']);
  } catch (e) {
    console.error('[x2t] conversion threw:', e);
    return null;
  }
  if (outputFormat === 'pdf') {
    console.log('[x2t] main1 return code for PDF:', rc);
  }

  try {
    return toStrictUint8Array(x2t.FS.readFile(outputPath));
  } catch (e) {
    if (outputFormat === 'pdf') {
      console.warn('[x2t] readFile failed for', outputPath, e);
      try {
        console.log('[x2t] /working contents:', x2t.FS.readdir('/working'));
      } catch {
        /* ignore */
      }
    }
    return null;
  }
}

/**
 * Convert an office file (docx, xlsx, pptx, etc.) to OnlyOffice internal .bin format.
 *
 * @param data - Raw file content
 * @param filename - Original filename (e.g. "report.docx")
 * @returns The .bin content and any extracted images
 */
export async function convertToInternal(
  data: ArrayBuffer,
  filename: string
): Promise<{
  bin: Uint8Array<ArrayBuffer>;
  images: Array<{ name: string; data: Uint8Array }>;
}> {
  const x2t = await getX2T();
  clearWorkingDir(x2t);
  const safeName = sanitize(filename);
  const ext = getExtension(safeName);
  const inputData = new Uint8Array(data);

  // Some formats need intermediate conversion (e.g. odt → docx → bin)
  let currentName = safeName;
  let currentData = inputData;

  const intermediateSteps: Array<{ source: string; format: string }> = [
    { source: 'ods', format: 'xlsx' },
    { source: 'odt', format: 'docx' },
    { source: 'odp', format: 'pptx' },
  ];

  for (const step of intermediateSteps) {
    if (ext === step.source) {
      const intermediate = runConversion(
        x2t,
        currentName,
        currentData,
        step.format
      );
      if (intermediate) {
        currentName = currentName + '.' + step.format;
        currentData = intermediate;
      }
    }
  }

  const bin = runConversion(x2t, currentName, currentData, 'bin');
  if (!bin) {
    throw new Error(`Failed to convert ${filename} to internal format`);
  }

  // Extract embedded images
  const images: Array<{ name: string; data: Uint8Array }> = [];
  try {
    const files = x2t.FS.readdir('/working/media/');
    for (const file of files) {
      if (file === '.' || file === '..') continue;
      const fileData = x2t.FS.readFile('/working/media/' + file, {
        encoding: 'binary',
      });
      images.push({ name: file, data: fileData });
    }
  } catch {
    // No media directory or empty
  }

  return { bin, images };
}

/**
 * Convert from OnlyOffice internal .bin format back to an office format.
 *
 * @param bin - The .bin content from editor.asc_nativeGetFile()
 * @param targetFormat - Target format (e.g. "docx", "xlsx", "pptx")
 * @param type - OnlyOffice document type ("doc", "sheet", "presentation")
 * @returns The converted file content
 */
export async function convertFromInternal(
  bin: ArrayBuffer,
  targetFormat: string,
  type?: string,
  media?: Map<string, Uint8Array>,
): Promise<Uint8Array<ArrayBuffer>> {
  const x2t = await getX2T();
  clearWorkingDir(x2t);
  const binData = new Uint8Array(bin);

  if (media && media.size > 0) {
    try {
      x2t.FS.mkdir('/working/media');
    } catch {
      /* exists */
    }
    for (const [name, bytes] of media) {
      try {
        x2t.FS.writeFile('/working/media/' + name, bytes);
      } catch (e) {
        console.warn('[x2t] failed to write media', name, e);
      }
    }
  }

  // .bin → intermediate Microsoft format if target is ODF
  const docType = type || EXTENSION_TO_X2T_TYPE[targetFormat] || 'doc';

  const intermediateFormats: Record<string, string> = {
    doc: 'docx',
    sheet: 'xlsx',
    presentation: 'pptx',
  };

  let currentName = 'document.bin';
  let currentData = binData;

  const intermediateFormat = intermediateFormats[docType];

  // If target IS the intermediate format (e.g. docx), single conversion
  if (intermediateFormat === targetFormat) {
    const result = runConversion(x2t, currentName, currentData, targetFormat);
    if (!result) {
      throw new Error(`Failed to convert from internal to ${targetFormat}`);
    }
    return result;
  }

  // Two-step: bin → intermediate MS format → target ODF format
  if (intermediateFormat) {
    const intermediate = runConversion(
      x2t,
      currentName,
      currentData,
      intermediateFormat
    );
    if (!intermediate) {
      throw new Error(`Failed to convert from internal to ${intermediateFormat} (step 1 of bin → ${targetFormat})`);
    }
    currentName = `document.${intermediateFormat}`;
    currentData = intermediate;
  }

  const result = runConversion(x2t, currentName, currentData, targetFormat);
  if (!result) {
    throw new Error(`Failed to convert from ${currentName} to ${targetFormat} (step 2)`);
  }
  return result;
}

/**
 * Convert to PDF using OO's dual-input mode.
 *
 * x2t's PDF writer doesn't take a single document binary and render it from
 * scratch — it needs TWO files side by side in the WASM FS:
 *   - the native .bin (canvas_word/cell/slide, from `asc_nativeGetFile()`),
 *     which carries the document content and structure;
 *   - a pre-computed PDF-layout binary at the hardcoded path `/working/pdf.bin`,
 *     produced by OO's `DrawingDocument.ToRendererPart()` and carrying the
 *     per-page layout the PDF writer then wraps into a real PDF file.
 *
 * For documents with embedded images, the PDF writer also reads each
 * referenced image from `/working/media/<name>` — without those files the
 * rendered PDF skips images entirely (most visible with Print Selection).
 */
export async function convertFromInternalToPdf(
  bin: ArrayBuffer,
  pdfLayoutBin: ArrayBuffer,
  media?: Map<string, Uint8Array>,
): Promise<Uint8Array<ArrayBuffer>> {
  const x2t = await getX2T();
  clearWorkingDir(x2t);
  await ensureFontsLoaded(x2t);

  // Pre-computed layout helper — x2t's PDF writer looks for this at a
  // hardcoded path, regardless of what's in params.xml.
  x2t.FS.writeFile('/working/pdf.bin', new Uint8Array(pdfLayoutBin));

  if (media) {
    try {
      x2t.FS.mkdir('/working/media');
    } catch {
      /* exists */
    }
    for (const [name, bytes] of media) {
      try {
        x2t.FS.writeFile('/working/media/' + name, bytes);
      } catch (e) {
        console.warn('[x2t] failed to write media file', name, e);
      }
    }
  }

  const result = runConversion(
    x2t,
    'document.bin',
    new Uint8Array(bin),
    'pdf',
  );
  if (!result) {
    throw new Error('Failed to convert .bin to pdf');
  }
  return result;
}
