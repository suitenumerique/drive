import {
  createEmptyFolderMarker,
  EMPTY_FOLDER_MARKER_NAME,
  getFileFromEntry,
  isEmptyFolderMarker,
  readAllEntries,
  traverseEntry,
} from "../dropTraversal";

// ---------------------------------------------------------------------------
// Fake FileSystemEntry helpers (no DataTransfer / no DragEvent involved)
// ---------------------------------------------------------------------------

const makeFileEntry = (
  fullPath: string,
  content = "",
): FileSystemFileEntry => {
  const name = fullPath.split("/").pop() ?? "";
  const file = new File([content], name, { type: "text/plain" });
  return {
    isFile: true,
    isDirectory: false,
    name,
    fullPath,
    file: (success: FileCallback) => success(file),
  } as unknown as FileSystemFileEntry;
};

const makeFailingFileEntry = (
  fullPath: string,
  error: unknown,
): FileSystemFileEntry => {
  const name = fullPath.split("/").pop() ?? "";
  return {
    isFile: true,
    isDirectory: false,
    name,
    fullPath,
    file: (_success: FileCallback, errorCb?: ErrorCallback) => {
      errorCb?.(error as DOMException);
    },
  } as unknown as FileSystemFileEntry;
};

/** Single-batch directory: readEntries returns children, then []. */
const makeDirEntry = (
  fullPath: string,
  children: FileSystemEntry[],
): FileSystemDirectoryEntry => {
  const name = fullPath.split("/").pop() ?? "";
  return {
    isFile: false,
    isDirectory: true,
    name,
    fullPath,
    createReader: () => makeReader([children, []]),
  } as unknown as FileSystemDirectoryEntry;
};

/** Build a reader that yields one batch per call until exhausted. */
const makeReader = (
  batches: FileSystemEntry[][],
): FileSystemDirectoryReader => {
  const queue = [...batches];
  return {
    readEntries: (success: FileSystemEntriesCallback) => {
      success(queue.shift() ?? []);
    },
  } as FileSystemDirectoryReader;
};

const makeFailingReader = (error: unknown): FileSystemDirectoryReader => {
  return {
    readEntries: (
      _success: FileSystemEntriesCallback,
      errorCb?: ErrorCallback,
    ) => {
      errorCb?.(error as DOMException);
    },
  } as FileSystemDirectoryReader;
};

// ===========================================================================
// createEmptyFolderMarker
// ===========================================================================

describe("createEmptyFolderMarker", () => {
  it("creates a zero-byte File", () => {
    const marker = createEmptyFolderMarker("/foo");
    expect(marker).toBeInstanceOf(File);
    expect(marker.size).toBe(0);
  });

  it("uses the standard marker name", () => {
    const marker = createEmptyFolderMarker("/foo");
    expect(marker.name).toBe(EMPTY_FOLDER_MARKER_NAME);
  });

  it("attaches a path of the form `<dirPath>/.empty-folder`", () => {
    const marker = createEmptyFolderMarker("/foo/bar");
    expect((marker as unknown as { path: string }).path).toBe(
      `/foo/bar/${EMPTY_FOLDER_MARKER_NAME}`,
    );
  });

  it("flags the marker with `isEmptyFolder: true`", () => {
    const marker = createEmptyFolderMarker("/foo");
    expect(
      (marker as unknown as { isEmptyFolder: boolean }).isEmptyFolder,
    ).toBe(true);
  });
});

// ===========================================================================
// isEmptyFolderMarker
// ===========================================================================

describe("isEmptyFolderMarker", () => {
  it("returns true for a marker created by createEmptyFolderMarker", () => {
    const marker = createEmptyFolderMarker("/foo");
    expect(isEmptyFolderMarker(marker)).toBe(true);
  });

  it("returns false for a regular File", () => {
    expect(isEmptyFolderMarker(new File(["hello"], "foo.txt"))).toBe(false);
  });

  it("returns false for a File whose name happens to be `.empty-folder`", () => {
    // The check must rely on the flag, NOT on the file name.
    expect(isEmptyFolderMarker(new File([], EMPTY_FOLDER_MARKER_NAME))).toBe(
      false,
    );
  });
});

// ===========================================================================
// getFileFromEntry
// ===========================================================================

describe("getFileFromEntry", () => {
  it("resolves with the underlying File", async () => {
    const entry = makeFileEntry("/foo.txt", "hello");
    const file = await getFileFromEntry(entry);
    expect(file).toBeInstanceOf(File);
    expect(file.name).toBe("foo.txt");
    expect(file.size).toBe(5);
  });

  it("attaches the entry's fullPath as `path`", async () => {
    const entry = makeFileEntry("/dir/sub/foo.txt");
    const file = await getFileFromEntry(entry);
    expect((file as unknown as { path: string }).path).toBe("/dir/sub/foo.txt");
  });

  it("rejects when the underlying file() call fails", async () => {
    const err = new DOMException("nope", "NotReadableError");
    const entry = makeFailingFileEntry("/bad.txt", err);
    await expect(getFileFromEntry(entry)).rejects.toBe(err);
  });
});

// ===========================================================================
// readAllEntries
// ===========================================================================

describe("readAllEntries", () => {
  it("returns an empty array when the reader yields no batches", async () => {
    const reader = makeReader([[]]);
    expect(await readAllEntries(reader)).toEqual([]);
  });

  it("returns all entries from a single batch", async () => {
    const a = makeFileEntry("/a.txt");
    const b = makeFileEntry("/b.txt");
    const reader = makeReader([[a, b], []]);
    const entries = await readAllEntries(reader);
    expect(entries).toEqual([a, b]);
  });

  it("concatenates entries across multiple batches (Safari-style)", async () => {
    const a = makeFileEntry("/a.txt");
    const b = makeFileEntry("/b.txt");
    const c = makeFileEntry("/c.txt");
    const d = makeFileEntry("/d.txt");
    // The native API forces a loop until an empty batch is returned.
    const reader = makeReader([[a, b], [c], [d], []]);
    const entries = await readAllEntries(reader);
    expect(entries).toEqual([a, b, c, d]);
  });

  it("calls readEntries until it yields an empty batch (loop terminates)", async () => {
    const spy = jest.fn();
    const queue: FileSystemEntry[][] = [
      [makeFileEntry("/a.txt")],
      [makeFileEntry("/b.txt")],
      [],
    ];
    const reader = {
      readEntries: (success: FileSystemEntriesCallback) => {
        spy();
        success(queue.shift() ?? []);
      },
    } as FileSystemDirectoryReader;

    await readAllEntries(reader);
    expect(spy).toHaveBeenCalledTimes(3);
  });

  it("rejects when readEntries calls the error callback", async () => {
    const err = new DOMException("boom", "NotReadableError");
    await expect(readAllEntries(makeFailingReader(err))).rejects.toBe(err);
  });
});

// ===========================================================================
// traverseEntry
// ===========================================================================

describe("traverseEntry", () => {
  it("returns a single FileWithPath for a file entry", async () => {
    const entry = makeFileEntry("/foo.txt", "x");
    const result = await traverseEntry(entry);
    expect(result).toHaveLength(1);
    expect((result[0] as unknown as { path: string }).path).toBe("/foo.txt");
    expect(isEmptyFolderMarker(result[0] as File)).toBe(false);
  });

  it("returns a single empty-folder marker for an empty directory", async () => {
    const dir = makeDirEntry("/empty", []);
    const result = await traverseEntry(dir);
    expect(result).toHaveLength(1);
    expect(isEmptyFolderMarker(result[0] as File)).toBe(true);
    expect((result[0] as unknown as { path: string }).path).toBe(
      `/empty/${EMPTY_FOLDER_MARKER_NAME}`,
    );
  });

  it("flattens a non-empty directory and emits no marker", async () => {
    const dir = makeDirEntry("/dir", [
      makeFileEntry("/dir/a.txt"),
      makeFileEntry("/dir/b.txt"),
    ]);
    const result = await traverseEntry(dir);
    const paths = (result as Array<File & { path: string }>)
      .map((f) => f.path)
      .sort();
    expect(paths).toEqual(["/dir/a.txt", "/dir/b.txt"]);
    expect(result.some((f) => isEmptyFolderMarker(f as File))).toBe(false);
  });

  it("recurses into nested directories and emits one marker per empty leaf", async () => {
    // /root
    //   /a    (empty)
    //   /b
    //     /c  (empty)
    //     b.txt
    const a = makeDirEntry("/root/a", []);
    const c = makeDirEntry("/root/b/c", []);
    const b = makeDirEntry("/root/b", [c, makeFileEntry("/root/b/b.txt")]);
    const root = makeDirEntry("/root", [a, b]);

    const result = await traverseEntry(root);

    const realPaths = (result as Array<File & { path: string }>)
      .filter((f) => !isEmptyFolderMarker(f))
      .map((f) => f.path)
      .sort();
    const markerPaths = (result as Array<File & { path: string }>)
      .filter((f) => isEmptyFolderMarker(f))
      .map((f) => f.path)
      .sort();

    expect(realPaths).toEqual(["/root/b/b.txt"]);
    expect(markerPaths).toEqual([
      `/root/a/${EMPTY_FOLDER_MARKER_NAME}`,
      `/root/b/c/${EMPTY_FOLDER_MARKER_NAME}`,
    ]);
  });

  it("returns an empty array for an entry that is neither file nor directory", async () => {
    const weird = {
      isFile: false,
      isDirectory: false,
      name: "weird",
      fullPath: "/weird",
    } as unknown as FileSystemEntry;
    expect(await traverseEntry(weird)).toEqual([]);
  });

  it("propagates errors from readAllEntries", async () => {
    const err = new DOMException("boom", "NotReadableError");
    const dir = {
      isFile: false,
      isDirectory: true,
      name: "boom",
      fullPath: "/boom",
      createReader: () => makeFailingReader(err),
    } as unknown as FileSystemDirectoryEntry;

    await expect(traverseEntry(dir)).rejects.toBe(err);
  });
});
