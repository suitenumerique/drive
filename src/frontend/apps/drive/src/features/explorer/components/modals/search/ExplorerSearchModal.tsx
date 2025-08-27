import { Modal, ModalProps, ModalSize } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

import { QuickSearch } from "@gouvfr-lasuite/ui-kit";
import { useRef, useState } from "react";
import { Item, ItemType } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import searchImage from "@/assets/search-dev.png";
import { ItemIcon } from "../../icons/ItemIcon";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "../../GlobalExplorerContext";

export const ExplorerSearchModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState<string>("");
  const searchUserTimeoutRef = useRef<NodeJS.Timeout>(null);
  const [items, setItems] = useState<Item[]>([]);
  const driver = getDriver();
  const [loading, setLoading] = useState(false);
  const { onNavigate, setPreviewItem, setPreviewItems } = useGlobalExplorer();

  const onSearch = (search: string) => {
    if (searchUserTimeoutRef.current) {
      clearTimeout(searchUserTimeoutRef.current);
    }

    searchUserTimeoutRef.current = setTimeout(async () => {
      setLoading(true);
      const items = await driver.searchItems({
        title: search,
      });
      setItems(items);
      setLoading(false);
    }, 300);
  };

  const onInputChange = (str: string) => {
    setInputValue(str);
    onSearch(str);
  };

  const onItemClick = (item: Item) => {
    if (item.type === ItemType.FOLDER) {
      onNavigate({
        item,
        type: NavigationEventType.ITEM,
      });
      props.onClose();
    } else {
      console.log("onItemClick", item);
      setPreviewItems([item]);
      setPreviewItem(item);
    }
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
          placeholder={t("explorer.search.modal.placeholder")}
        >
          {items.length > 0 ? (
            <div className="explorer__search__modal__items">
              <div className="explorer__search__modal__items__title">
                {t("explorer.search.modal.results")}
              </div>
              {items.map((item) => (
                <SearchItem key={item.id} item={item} onClick={onItemClick} />
              ))}
            </div>
          ) : (
            <div className="explorer__search__modal__empty">
              <img src={searchImage.src} alt="" width={200} height={200} />
            </div>
          )}
        </QuickSearch>
      </div>
    </Modal>
  );
};

const SearchItem = ({
  item,
  onClick,
}: {
  item: Item;
  onClick: (item: Item) => void;
}) => {
  return (
    <button
      className="explorer__search__modal__item"
      onClick={() => {
        onClick(item);
      }}
    >
      <div className="explorer__search__modal__item__icon">
        <ItemIcon item={item} />
      </div>
      <div className="explorer__search__modal__item__content">
        <div className="explorer__search__modal__item__content__title">
          {item.title}
        </div>
        <div className="explorer__search__modal__item__content__ancestors">
          {item.parents?.map((ancestor) => ancestor.title).join(" / ")}
        </div>
      </div>
    </button>
  );
};
