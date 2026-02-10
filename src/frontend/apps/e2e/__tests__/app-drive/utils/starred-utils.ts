import { Page, expect } from "@playwright/test";
import { getItemTree, openTreeNode } from "../utils-tree";
import {
  clickOnRowItemActions,
  expectRowItem,
  expectRowItemIsNotVisible,
} from "../utils-embedded-grid";
import { clickToFavorites } from "../utils-navigate";

export const verifyItemIsStarred = async (page: Page, itemName: string) => {
  await openTreeNode(page, "Starred");
  await getItemTree(page, itemName); // get and verify the item is in the tree
  await clickToFavorites(page);
  await expectRowItem(page, itemName);
};

export const verifyItemIsNotStarred = async (page: Page, itemName: string) => {
  await openTreeNode(page, "Starred");
  await getItemTree(page, itemName, false);
  await clickToFavorites(page);
  await expectRowItemIsNotVisible(page, itemName);
};

export const starItem = async (page: Page, itemName: string) => {
  await clickOnRowItemActions(page, itemName, "Star");
};

export const unstarItem = async (page: Page, itemName: string) => {
  await clickOnRowItemActions(page, itemName, "Unstar");
};
