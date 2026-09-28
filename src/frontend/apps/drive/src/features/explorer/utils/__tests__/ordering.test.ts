import { ColumnType, SortState } from "../../types/columns";
import { ViewConfig } from "../../types/viewConfig";
import { computeOrdering, computeFilters } from "../ordering";

const foldersFirst: ViewConfig = {
  defaultOrdering: "-type,title",
  folderMode: "folders_first",
};

const filesOnly: ViewConfig = {
  defaultOrdering: "-updated_at",
  folderMode: "files_only",
};

const mixed: ViewConfig = {
  defaultOrdering: "-updated_at",
  folderMode: "mixed",
};

describe("computeOrdering", () => {
  it("returns default ordering when sortState is null", () => {
    expect(computeOrdering(foldersFirst, null)).toBe("-type,title");
    expect(computeOrdering(filesOnly, null)).toBe("-updated_at");
    expect(computeOrdering(mixed, null)).toBe("-updated_at");
  });

  it("returns ascending ordering for title", () => {
    const sort: SortState = { columnId: "title", direction: "asc" };
    expect(computeOrdering(foldersFirst, sort)).toBe("title");
  });

  it("returns descending ordering for title", () => {
    const sort: SortState = { columnId: "title", direction: "desc" };
    expect(computeOrdering(foldersFirst, sort)).toBe("-title");
  });

  it("returns ascending ordering for each column type", () => {
    const cases: [ColumnType, string][] = [
      [ColumnType.LAST_MODIFIED, "updated_at"],
      [ColumnType.CREATED, "created_at"],
      [ColumnType.CREATED_BY, "creator__full_name"],
      [ColumnType.FILE_TYPE, "mime_category"],
      [ColumnType.FILE_SIZE, "size"],
    ];
    for (const [columnType, expectedField] of cases) {
      const sort: SortState = { columnId: columnType, direction: "asc" };
      expect(computeOrdering(foldersFirst, sort)).toBe(expectedField);
    }
  });

  it("returns descending ordering for each column type", () => {
    const cases: [ColumnType, string][] = [
      [ColumnType.LAST_MODIFIED, "-updated_at"],
      [ColumnType.CREATED, "-created_at"],
      [ColumnType.CREATED_BY, "-creator__full_name"],
      [ColumnType.FILE_TYPE, "-mime_category"],
      [ColumnType.FILE_SIZE, "-size"],
    ];
    for (const [columnType, expectedField] of cases) {
      const sort: SortState = { columnId: columnType, direction: "desc" };
      expect(computeOrdering(foldersFirst, sort)).toBe(expectedField);
    }
  });

  it("drops -type prefix when user sorts explicitly on folders_first view", () => {
    const sort: SortState = { columnId: ColumnType.FILE_SIZE, direction: "asc" };
    // Should NOT be "-type,size", just "size"
    expect(computeOrdering(foldersFirst, sort)).toBe("size");
  });
});

describe("computeFilters", () => {
  it("adds ordering to base filters", () => {
    const result = computeFilters(foldersFirst, { is_creator_me: true }, null);
    expect(result.ordering).toBe("-type,title");
    expect(result.is_creator_me).toBe(true);
  });

  it("overrides ordering with explicit sort", () => {
    const sort: SortState = { columnId: "title", direction: "asc" };
    const result = computeFilters(foldersFirst, {}, sort);
    expect(result.ordering).toBe("title");
  });

  it("adds type=file filter for files_only mode", () => {
    const result = computeFilters(filesOnly, {}, null);
    expect(result.type).toBe("file");
    expect(result.ordering).toBe("-updated_at");
  });

  it("keeps type=file filter even when sorting explicitly in files_only mode", () => {
    const sort: SortState = { columnId: ColumnType.FILE_SIZE, direction: "desc" };
    const result = computeFilters(filesOnly, {}, sort);
    expect(result.type).toBe("file");
    expect(result.ordering).toBe("-size");
  });

  it("does not add type filter for mixed mode", () => {
    const result = computeFilters(mixed, {}, null);
    expect(result.type).toBeUndefined();
  });

  it("does not add type filter for folders_first mode", () => {
    const result = computeFilters(foldersFirst, {}, null);
    expect(result.type).toBeUndefined();
  });

  it("preserves all base filters", () => {
    const base = { is_creator_me: true, is_favorite: true, page_size: 50 };
    const result = computeFilters(foldersFirst, base, null);
    expect(result.is_creator_me).toBe(true);
    expect(result.is_favorite).toBe(true);
    expect(result.page_size).toBe(50);
  });
});
