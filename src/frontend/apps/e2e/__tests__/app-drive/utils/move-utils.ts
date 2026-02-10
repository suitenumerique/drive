import { expect } from "@playwright/test";

import { PageOrLocator } from "./types-utils";
import { getRowItem } from "../utils-embedded-grid";

export const getMoveFolderModal = async (page: PageOrLocator) => {
  const moveFolderModal = page.getByLabel("Move folder modal");
  await expect(moveFolderModal).toBeVisible();
  return moveFolderModal;
};

export const getMoveConfirmationModal = async (page: PageOrLocator) => {
  const moveConfirmationModal = page.getByLabel("Move confirmation modal");
  await expect(moveConfirmationModal).toBeVisible();
  return moveConfirmationModal;
};
export const expectMoveFolderModal = async (page: PageOrLocator) => {
  await getMoveFolderModal(page); // getMoveFolderModal already checks if the modal is visible
};

export const acceptMoveItem = async (page: PageOrLocator) => {
  const moveFolderModal = await getMoveFolderModal(page);
  await moveFolderModal.getByRole("button", { name: "Move here" }).click();
  const moveConfirmationModal = await getMoveConfirmationModal(page);
  await expect(
    moveConfirmationModal.getByText("Transfer rights")
  ).toBeVisible();
  await expect(
    moveConfirmationModal.getByText("You are about to move the")
  ).toBeVisible();
  await moveConfirmationModal
    .getByRole("button", { name: "Move anyway" })
    .click();
};

export const searchAndSelectItem = async (
  page: PageOrLocator,
  itemName: string
) => {
  const moveFolderModal = await getMoveFolderModal(page);
  await moveFolderModal.getByPlaceholder("Search for a folder").click();
  await moveFolderModal.getByPlaceholder("Search for a folder").fill(itemName);
  await expect(moveFolderModal.getByText("Search results")).toBeVisible();
  const folderToSelect = await getRowItem(moveFolderModal, itemName);
  await folderToSelect.dblclick();
};

export const clickAndAcceptMoveToRoot = async (page: PageOrLocator) => {
  const moveFolderModal = await getMoveFolderModal(page);
  await moveFolderModal.getByRole("button", { name: "Move to root" }).click();
  const moveConfirmationModal = await getMoveConfirmationModal(page);
  await expect(
    moveConfirmationModal.getByText(
      "Moved documents will be accessible via your 'My files' tab. People who had access to the documents only through inherited rights from a parent will no longer be able to access them."
    )
  ).toBeVisible();
  await moveConfirmationModal
    .getByRole("button", { name: "Move anyway" })
    .click();
};
