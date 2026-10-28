import { Driver } from "@/features/drivers/Driver";
import { Item, ItemType } from "@/features/drivers/types";
import { fetchSubtree } from "../flattenSubtree";

const item = (
  id: string,
  title: string,
  path: string,
  type = ItemType.FILE,
): Item => ({ id, title, path, type }) as unknown as Item;

describe("fetchSubtree", () => {
  it("lists the root, then each folder's content right under it, folders first and by name", async () => {
    const root = item("r", "Project", "r", ItemType.FOLDER);
    // In the API's order: by path, made of ids.
    const descendants = [
      root,
      item("a", "File 10.pdf", "r.a"),
      item("b", "Drafts", "r.b", ItemType.FOLDER),
      item("c", "notes.txt", "r.b.c"),
      item("d", "Archive", "r.d", ItemType.FOLDER),
      item("e", "File 2.pdf", "r.e"),
      item("f", "Budget.ods", "r.b.f"),
    ];
    const driver = {
      getDescendants: async () => descendants,
    } as unknown as Driver;

    const nodes = await fetchSubtree(driver, root);

    expect(nodes.map((n) => n.item.title)).toEqual([
      "Project",
      "Archive",
      "Drafts",
      "Budget.ods",
      "notes.txt",
      "File 2.pdf",
      "File 10.pdf",
    ]);
  });
});
