import { clearDb, login } from "./utils-common";

import test from "@playwright/test";
import {
  addChildrenFromTreeItem,
  checkTreeItemIsSelected,
  clickOnItemInTree,
  deleteFolderInTree,
  deleteWorkspaceInTree,
  toggleItemInTree,
} from "./utils-tree";
import { createFolder, createWorkspace } from "./utils-item";
import { checkExplorerBreadcrumbs } from "./utils-explorer";

test("Checks that if one of the parents of the current folder is deleted, it redirects to the highest parent", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await addChildrenFromTreeItem(page, "My workspace", "Test");
  await toggleItemInTree(page, "My workspace");
  await clickOnItemInTree(page, "Test");
  await checkExplorerBreadcrumbs(page, ["My workspace", "Test"]);
  await addChildrenFromTreeItem(page, "Test", "SubTest");
  await clickOnItemInTree(page, "SubTest");
  await checkExplorerBreadcrumbs(page, ["My workspace", "Test", "SubTest"]);
  await deleteFolderInTree(page, "Test");
  await checkTreeItemIsSelected(page, "My workspace");
  await checkExplorerBreadcrumbs(page, ["My workspace"]);
});

test("Check that if we delete the current workspace, it redirects to the main workspace", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await createWorkspace(page, "TestWorkspace");
  await clickOnItemInTree(page, "TestWorkspace");
  await checkExplorerBreadcrumbs(page, ["TestWorkspace"]); // groups is the icon for the workspace
  await createFolder(page, "TestFolder");
  await deleteWorkspaceInTree(page, "TestWorkspace");
  await checkTreeItemIsSelected(page, "My workspace");
  await checkExplorerBreadcrumbs(page, ["My workspace"]);
});
