import { clearDb, login } from "./utils-common";

import test from "@playwright/test";
import {
  addChildrenFromTreeItem,
  expectTreeItemIsSelected,
  clickOnItemInTree,
  deleteFolderInTree,
  deleteWorkspaceInTree,
  toggleItemInTree,
} from "./utils-tree";
import { createFolder, createWorkspace } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";

test("Checks that if one of the parents of the current folder is deleted, it redirects to the highest parent", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await addChildrenFromTreeItem(page, "My workspace", "Test");
  await clickOnItemInTree(page, "Test");
  await expectExplorerBreadcrumbs(page, ["My workspace", "Test"]);
  await addChildrenFromTreeItem(page, "Test", "SubTest");
  await clickOnItemInTree(page, "SubTest");
  await expectExplorerBreadcrumbs(page, ["My workspace", "Test", "SubTest"]);
  await deleteFolderInTree(page, "Test");
  await expectTreeItemIsSelected(page, "My workspace");
  await expectExplorerBreadcrumbs(page, ["My workspace"]);
});

test("Check that if we delete the current workspace, it redirects to the main workspace", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await createWorkspace(page, "TestWorkspace");
  await clickOnItemInTree(page, "TestWorkspace");
  await expectExplorerBreadcrumbs(page, ["TestWorkspace"]); // groups is the icon for the workspace
  await createFolder(page, "TestFolder");
  await deleteWorkspaceInTree(page, "TestWorkspace");
  await expectTreeItemIsSelected(page, "My workspace");
  await expectExplorerBreadcrumbs(page, ["My workspace"]);
});
