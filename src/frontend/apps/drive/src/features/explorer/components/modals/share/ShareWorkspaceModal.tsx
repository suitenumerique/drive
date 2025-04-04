import { Access, Item } from "@/features/drivers/types";
import { useItemAccesses } from "@/features/explorer/hooks/useQueries";
import {
  QuickSearch,
  QuickSearchData,
  QuickSearchGroup,
} from "@gouvfr-lasuite/ui-kit";
import { Modal, ModalSize } from "@openfun/cunningham-react";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AccessRowItem } from "./items/AccessRowItem";
import { useUsers } from "@/features/users/hooks/useUserQueries";

type ShareWorkspaceModalProps = {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
};

export const ShareWorkspaceModal = ({
  isOpen,
  onClose,
  item,
}: ShareWorkspaceModalProps) => {
  const { t } = useTranslation();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [queryValue, setQueryValue] = useState("");
  const { data: accesses } = useItemAccesses(item.id);
  //   const { data: invitations } = useItemInvitations(item.id);
  const { data: users } = useUsers(
    { q: queryValue },
    { enabled: !!queryValue && queryValue !== "" }
  );

  console.log("users", users);

  const search = (search: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setQueryValue(search);
    }, 500);
  };

  const accessesData: QuickSearchData<Access> = useMemo(() => {
    const members = accesses;
    const count = accesses?.length ?? 1;

    return {
      groupName:
        count === 1
          ? t("Document owner")
          : t("Share with {{count}} users", {
              count: count,
            }),
      elements: members ?? [],
    };
  }, [accesses, t]);

  return (
    <Modal
      title="Partager le dossier"
      isOpen={isOpen}
      onClose={onClose}
      size={ModalSize.LARGE}
    >
      <QuickSearch
        onFilter={(str) => {
          search(str);
          setInputValue(str);
        }}
        inputValue={inputValue}
        loading={false}
        placeholder={t("Type a name or email")}
      >
        <QuickSearchGroup
          group={accessesData}
          onSelect={(access) => {
            console.log("access", access);
          }}
          renderElement={(access) => <AccessRowItem access={access} />}
        />
      </QuickSearch>
    </Modal>
  );
};
