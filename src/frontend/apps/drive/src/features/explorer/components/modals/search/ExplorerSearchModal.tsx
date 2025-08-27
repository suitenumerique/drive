import { Modal, ModalProps, ModalSize } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

import { QuickSearch } from "@gouvfr-lasuite/ui-kit";
import { useRef, useState } from "react";
import { Item, ItemType } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";

export const ExplorerSearchModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState<string>("");
  const searchUserTimeoutRef = useRef<NodeJS.Timeout>(null);
  const [items, setItems] = useState<Item[]>([]);
  const driver = getDriver();
  const [loading, setLoading] = useState(false);

  const onSearch = (search: string) => {
    if (searchUserTimeoutRef.current) {
      clearTimeout(searchUserTimeoutRef.current);
    }

    searchUserTimeoutRef.current = setTimeout(async () => {
      setLoading(true);
      const items = await driver.searchItems({
        title: search,
        type: ItemType.FILE,
      });
      console.log(items);
      setItems(items);
      setLoading(false);
    }, 300);
  };

  const onInputChange = (str: string) => {
    setInputValue(str);
    onSearch(str);
  };

  return (
    <Modal
      {...props}
      closeOnClickOutside
      size={ModalSize.MEDIUM}
      title={t("explorer.search.modal.title")}
    >
      <div className="explorer__search__modal">
        <QuickSearch
          onFilter={onInputChange}
          inputValue={inputValue}
          loading={loading}
          placeholder={t("components.share.user.placeholder")}
        >
          {items.map((item) => (
            <div key={item.id}>{item.title}</div>
          ))}
        </QuickSearch>
      </div>
    </Modal>
  );
};
