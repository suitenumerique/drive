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
function runConversion(
  x2t: X2TModule,
  inputName: string,
  inputData: Uint8Array,
  outputFormat: string
): Uint8Array | null {
  x2t.FS.writeFile('/working/' + inputName, inputData);

  const params = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<TaskQueueDataConvert',
    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
    '  xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
    `  <m_sFileFrom>/working/${inputName}</m_sFileFrom>`,
    '  <m_sThemeDir>/working/themes</m_sThemeDir>',
    `  <m_sFileTo>/working/${inputName}.${outputFormat}</m_sFileTo>`,
    '  <m_bIsNoBase64>false</m_bIsNoBase64>',
    '</TaskQueueDataConvert>',
  ].join('\n');

  x2t.FS.writeFile('/working/params.xml', params);

  try {
    x2t.ccall('main1', 'number', ['string'], ['/working/params.xml']);
  } catch (e) {
    console.error('x2t conversion failed:', e);
    return null;
  }

  try {
    return x2t.FS.readFile('/working/' + inputName + '.' + outputFormat);
  } catch {
    console.error('Failed to read converted output');
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
  bin: Uint8Array;
  images: Array<{ name: string; data: Uint8Array }>;
}> {
  const x2t = await getX2T();
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
  type?: string
): Promise<Uint8Array> {
  const x2t = await getX2T();
  const binData = new Uint8Array(bin);

  // .bin → intermediate Microsoft format if target is ODF
  const docType = type || EXTENSION_TO_X2T_TYPE[targetFormat] || 'doc';

  const intermediateFormats: Record<string, string> = {
    doc: 'docx',
    sheet: 'xlsx',
    presentation: 'pptx',
  };

  let currentName = 'document.bin';
  let currentData = binData;

  // First convert bin → intermediate MS format
  const intermediateFormat = intermediateFormats[docType];
  if (intermediateFormat && intermediateFormat !== targetFormat) {
    const intermediate = runConversion(
      x2t,
      currentName,
      currentData,
      intermediateFormat
    );
    if (intermediate) {
      currentName = currentName + '.' + intermediateFormat;
      currentData = intermediate;
    }
  }

  // Then convert to final target if different
  if (intermediateFormat === targetFormat) {
    const result = runConversion(x2t, currentName, currentData, targetFormat);
    if (!result) {
      throw new Error(`Failed to convert from internal to ${targetFormat}`);
    }
    return result;
  }

  const result = runConversion(x2t, currentName, currentData, targetFormat);
  if (!result) {
    throw new Error(`Failed to convert from internal to ${targetFormat}`);
  }
  return result;
}
