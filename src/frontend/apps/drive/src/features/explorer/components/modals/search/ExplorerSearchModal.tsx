import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
  useModals,
} from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";

import {
  QuickSearch,
  QuickSearchGroup,
  QuickSearchItemTemplate,
} from "@gouvfr-lasuite/ui-kit";
import { useEffect, useRef, useState } from "react";
import { Item, ItemType } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { ItemIcon } from "../../icons/ItemIcon";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "../../GlobalExplorerContext";
import {
  ExplorerFilterType,
  ExplorerFilterWorkspace,
  ExplorerFilterScope,
  handleFilterChange,
} from "../../app-view/ExplorerFilters";
import { ItemFilters } from "@/features/drivers/Driver";
import { Key } from "react-aria-components";
import { clearFromRoute, getItemTitle } from "@/features/explorer/utils/utils";
import { messageModalTrashNavigate } from "../../trash/utils";
import { useIsMinimalLayout } from "@/utils/useLayout";

type ExplorerSearchModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  defaultFilters?: ItemFilters;
};

export const ExplorerSearchModal = (props: ExplorerSearchModalProps) => {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState<string>("");
  const isMinimalLayout = useIsMinimalLayout();
  const [filters, setFilters] = useState<ItemFilters>(
    props.defaultFilters || {},
  );

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

  const modals = useModals();

  const onItemClick = (item: Item) => {
    if (item.type === ItemType.FOLDER) {
      if (item.deleted_at) {
        messageModalTrashNavigate(modals);
      } else {
        clearFromRoute();
        onNavigate({
          item,
          type: NavigationEventType.ITEM,
        });
        props.onClose();
      }
    } else {
      setPreviewItems([item]);
      setPreviewItem(item);
      inputTextSelected.current = false;
    }
  };

  const inputTextSelected = useRef<boolean>(false);
  useEffect(() => {
    if (!props.isOpen) {
      inputTextSelected.current = false;
    }
  }, [props.isOpen]);

  return (
    <Modal
      {...props}
      closeOnClickOutside
      size={ModalSize.MEDIUM}
      title={t("explorer.search.modal.title")}
    >
      <div
        className="explorer__search__modal"
        ref={(ref) => {
          if (inputTextSelected.current) {
            return;
          }
          // We select the input content when the modal is opened.
          const input = ref?.querySelector(
            ".quick-search-input-container input",
          ) as HTMLInputElement;
          input?.focus();
          input?.select();
          inputTextSelected.current = true;
        }}
      >
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
                isDisabled={isMinimalLayout}
                onChange={(value) => onFilterChange("workspace", value)}
              />
              <ExplorerFilterScope
                value={filters?.scope ?? null}
                onChange={(value) => onFilterChange("scope", value)}
              />
            </div>

            <div>
              {Object.keys(filters).length > 0 && (
                <Button
                  variant="tertiary"
                  size="small"
                  onClick={() => setFilters({})}
                >
                  {t("explorer.search.modal.filters.reset")}
                </Button>
              )}
            </div>
          </div>
          {items.length > 0 && (
            <div className="explorer__search__modal__items__container">
              <div className="explorer__search__modal__items">
                <QuickSearchGroup
                  onSelect={onItemClick}
                  renderElement={(element) => <SearchItem item={element} />}
                  group={{
                    groupName: t("explorer.search.modal.results"),
                    elements: items,
                  }}
                />
              </div>
            </div>
          )}
        </QuickSearch>
      </div>
    </Modal>
  );
};

const SearchItem = ({ item }: { item: Item }) => {
  const { t } = useTranslation();
  const shouldShowAncestors =
    (item.parents && item.parents.length > 0) || item.deleted_at;
  return (
    <QuickSearchItemTemplate
      right={
        <span className="material-icons explorer__search__modal__item__right-icon">
          keyboard_return
        </span>
      }
      left={
        <div
          className="explorer__search__modal__item"
          data-testid="search-item"
        >
          <div className="explorer__search__modal__item__icon">
            <ItemIcon item={item} />
          </div>
          <div className="explorer__search__modal__item__content">
            <div className="explorer__search__modal__item__content__title">
              {getItemTitle(item)}
            </div>
            {shouldShowAncestors && (
              <div className="explorer__search__modal__item__content__ancestors">
                {item.deleted_at
                  ? t("explorer.tree.trash")
                  : item.parents
                      ?.map((ancestor) => getItemTitle(ancestor))
                      .join(" / ")}
              </div>
            )}
          </div>
        </div>
      }
    />
  );
};
