import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

import { QuickSearch } from "@gouvfr-lasuite/ui-kit";
import { useEffect, useRef, useState } from "react";
import { Item, ItemType } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import searchImage from "@/assets/search-dev.png";
import { ItemIcon } from "../../icons/ItemIcon";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "../../GlobalExplorerContext";
import {
  ExplorerFilterType,
  ExplorerFilterWorkspace,
  handleFilterChange,
} from "../../app-view/ExplorerFilters";
import { ItemFilters } from "@/features/drivers/Driver";
import { Key } from "react-aria-components";

export const ExplorerSearchModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState<string>("");
  const [filters, setFilters] = useState<ItemFilters>({});
  const searchUserTimeoutRef = useRef<NodeJS.Timeout>(null);
  const [items, setItems] = useState<Item[]>([]);

  const driver = getDriver();
  const [loading, setLoading] = useState(false);
  const { onNavigate, setPreviewItem, setPreviewItems } = useGlobalExplorer();

  const onSearch = () => {
    if (searchUserTimeoutRef.current) {
      clearTimeout(searchUserTimeoutRef.current);
    }

    if (inputValue === "" && Object.keys(filters).length === 0) {
      setItems([]);
      return;
    }

    searchUserTimeoutRef.current = setTimeout(async () => {
      setLoading(true);
      const items = await driver.searchItems({
        ...filters,
        title: inputValue,
      });
      setItems(items);
      setLoading(false);
    }, 300);
  };

  useEffect(() => {
    onSearch();
  }, [filters, inputValue]);

  const onInputChange = (str: string) => {
    setInputValue(str);
  };

  const onFilterChange = (name: string, value: Key | null) => {
    setFilters(handleFilterChange(filters, name, value));
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
          <div className="explorer__search__modal__filters">
            <div className="explorer__search__modal__filters__inputs">
              <ExplorerFilterType
                value={filters?.type ?? null}
                onChange={(value) => onFilterChange("type", value)}
              />
              <ExplorerFilterWorkspace
                value={filters?.workspace ?? null}
                onChange={(value) => onFilterChange("workspace", value)}
              />
            </div>
            <Button
              color="primary-text"
              size="small"
              onClick={() => setFilters({})}
            >
              {t("explorer.search.modal.filters.reset")}
            </Button>
          </div>
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
