import {
  Button,
  IconSize,
  Modal,
  ModalSize,
  Tooltip,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";
import { Item, ItemType } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { EncryptionModalContent } from "./EncryptionLayout";
import { useIsCut } from "./recursive/JobFileRow";
import {
  RESTED_TOOLTIP_CLASS,
  RestedTooltipText,
} from "./recursive/RestedTooltipText";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
}

/**
 * Shown on "Remove encryption" for an item inside an encrypted folder:
 * encryption is removed from that folder only, so the modal shows it and
 * leads there.
 */
export const ModalEncryptionNotRoot = ({ isOpen, onClose, item }: Props) => {
  const { t } = useTranslation();
  const router = useRouter();

  const { data: keyChain } = useQuery({
    queryKey: ["key-chain", item.id],
    queryFn: () => getDriver().getKeyChain(item.id),
    enabled: isOpen,
  });
  const rootId =
    keyChain?.encryption_tree_root_item_id ?? keyChain?.user_access_item_id;
  const { data: root } = useItem(rootId ?? "", { enabled: !!rootId });

  const title = t(
    "encryption.not_root_modal.title",
    "Encrypted with its folder",
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size={ModalSize.SMALL}
      aria-label={title}
    >
      <EncryptionModalContent
        illustration="folder-shield"
        title={title}
        description={
          item.type === ItemType.FOLDER
            ? t(
                "encryption.not_root_modal.body_folder",
                "This folder is encrypted with the folder below. Encryption can only be removed from that folder, which also decrypts everything inside it.",
              )
            : t(
                "encryption.not_root_modal.body_file",
                "This file is encrypted with the folder below. Encryption can only be removed from that folder, which also decrypts everything inside it.",
              )
        }
        actions={
          <Button
            disabled={!rootId}
            onClick={() => {
              onClose();
              void router.push(`/explorer/items/${rootId}`);
            }}
          >
            {t("encryption.not_root_modal.open_folder", "Open the folder")}
          </Button>
        }
      >
        {root && <FolderRow folder={root} />}
      </EncryptionModalContent>
    </Modal>
  );
};

/** The folder as a row of the recursive modals' list. */
const FolderRow = ({ folder }: { folder: Item }) => {
  const { ref, isCut } = useIsCut(folder.title);
  const name = (
    <p className="drive__encryption-job-row__name">{folder.title}</p>
  );

  return (
    <div className="drive__encryption-modal__folder">
      <div className="drive__encryption-job-row">
        <ItemIcon item={folder} size={IconSize.LARGE} />
        <div ref={ref} className="drive__encryption-job-row__name-cell">
          {isCut ? (
            <Tooltip
              content={<RestedTooltipText text={folder.title} />}
              placement="top"
              className={RESTED_TOOLTIP_CLASS}
            >
              {name}
            </Tooltip>
          ) : (
            name
          )}
        </div>
      </div>
    </div>
  );
};
