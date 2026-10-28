import { renderToStaticMarkup } from "react-dom/server";
import { Item, ItemType } from "@/features/drivers/types";
import { JobFileList } from "../JobFileList";
import { FileJobRow } from "../types";

// The icon and the size formatting read Drive's config: not what these tests
// are about.
jest.mock("@/features/explorer/components/icons/ItemIcon", () => ({
  ItemIcon: () => null,
}));
jest.mock("@/features/explorer/utils/utils", () => ({
  formatSize: (size: number) => `${size} B`,
}));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: unknown, options?: Record<string, string>) =>
      typeof fallback === "string"
        ? fallback.replace(/{{(\w+)}}/g, (_, k) => options?.[k] ?? "")
        : key,
  }),
}));

const row = (
  i: number,
  state: FileJobRow["state"] = "pending",
): FileJobRow => ({
  id: `item-${i}`,
  title: `File ${i}.pdf`,
  path: "",
  state,
  error: state === "failed" ? "Download failed: 404" : undefined,
  item: {
    id: `item-${i}`,
    title: `File ${i}.pdf`,
    type: ItemType.FILE,
    mimetype: "application/pdf",
    size: 1024,
  } as unknown as Item,
});

const renderedTitles = (html: string) =>
  [
    ...html.matchAll(/class="drive__encryption-job-row__name"[^>]*>([^<]*)</g),
  ].map((m) => m[1]);

describe("JobFileList", () => {
  it("shows the file that failed first, where the reason the job stopped is in view", () => {
    const rows = [row(1, "staged"), row(2, "staged"), row(3, "failed"), row(4)];

    const titles = renderedTitles(
      renderToStaticMarkup(<JobFileList rows={rows} mode="encrypt" />),
    );

    expect(titles).toEqual([
      "File 3.pdf",
      "File 1.pdf",
      "File 2.pdf",
      "File 4.pdf",
    ]);
  });

  it("renders only the rows around the visible window of a large job", () => {
    const rows = Array.from({ length: 5000 }, (_, i) => row(i));

    const titles = renderedTitles(
      renderToStaticMarkup(<JobFileList rows={rows} mode="encrypt" />),
    );

    expect(titles.length).toBeGreaterThan(3);
    expect(titles.length).toBeLessThan(20);
    expect(titles[0]).toBe("File 0.pdf");
  });
});
