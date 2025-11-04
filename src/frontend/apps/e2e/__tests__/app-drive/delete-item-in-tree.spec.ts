import { clearDb, login } from "./utils-common";

import test from "@playwright/test";
import {
  addChildrenFromTreeItem,
  expectTreeItemIsSelected,
  clickOnItemInTree,
  openTreeNode,
  deleteFolderInTree,
  deleteWorkspaceInTree,
} from "./utils-tree";
import { createWorkspace } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";

test("Checks that if one of the parents of the current folder is deleted, it redirects to the highest parent", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await addChildrenFromTreeItem(page, "My workspace", "Test");
  await openTreeNode(page, "My workspace");
  await clickOnItemInTree(page, "Test");
  await expectExplorerBreadcrumbs(page, ["My workspace", "Test"]);
  await addChildrenFromTreeItem(page, "Test", "SubTest");
  await openTreeNode(page, "Test");
  await clickOnItemInTree(page, "SubTest");
  await expectExplorerBreadcrumbs(page, ["My workspace", "Test", "SubTest"]);
  await deleteFolderInTree(page, "Test");
  await expectTreeItemIsSelected(page, "My workspace", false);
  await expectExplorerBreadcrumbs(page, ["My workspace"]);
});

test("Check that if we delete the current workspace, it redirects to the main workspace", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await createWorkspace(page, "TestWorkspace");
  await openTreeNode(page, "Shared Space");
  await clickOnItemInTree(page, "TestWorkspace");
  await expectExplorerBreadcrumbs(page, ["TestWorkspace"]); // groups is the icon for the workspace
  await deleteWorkspaceInTree(page, "TestWorkspace");
});
