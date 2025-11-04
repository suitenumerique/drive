import { Item, LinkReach } from "@/features/drivers/types";
import { useMutationUpdateItem } from "@/features/explorer/hooks/useMutations";
import { useClipboard } from "@/hooks/useCopyToClipboard";
import { ShareModal, ShareModalCopyLinkFooter } from "@gouvfr-lasuite/ui-kit";
import { ModalProps } from "@openfun/cunningham-react";

type FileShareModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  item: Item;
};

export const FileShareModal = ({ item, ...props }: FileShareModalProps) => {
  const updateItem = useMutationUpdateItem();
  const copyToClipboard = useClipboard();
  return (
    <ShareModal
      linkSettings={true}
      linkReachChoices={[
        {
          value: "public",
        },
        {
          value: "restricted",
        },
      ]}
      linkReach={item.link_reach}
      onUpdateLinkReach={(value) => {
        updateItem.mutate({
          id: item.id,
          link_reach: value as LinkReach,
        });
      }}
      canUpdate={item.abilities?.update}
      hideInvitations={true}
      hideMembers={true}
      outsideSearchContent={
        <ShareModalCopyLinkFooter
          onCopyLink={() => {
            const url =
              window.location.origin + "/explorer/items/files/" + item.id;
            copyToClipboard(url);
          }}
          onOk={() => {
            props.onClose();
          }}
        />
      }
      {...props}
    >
      COUCOU
    </ShareModal>
  );
};
