import {
  QuickSearch,
  QuickSearchData,
  QuickSearchGroup,
  QuickSearchItemTemplate,
} from "@gouvfr-lasuite/ui-kit";
import { Modal, ModalSize, Tooltip } from "@openfun/cunningham-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useItems } from "../../hooks/useQueries";
import { Item, ItemType } from "@/features/drivers/types";
import { useRouter } from "next/router";
import { ItemIcon } from "../ItemIcon";
import { useTranslation } from "react-i18next";
import emptySearch from "@/assets/search/empty_search.png";

type SearchModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export const SearchModal = ({ isOpen, onClose }: SearchModalProps) => {
  const router = useRouter();
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState("");
  const [queryString, setQueryString] = useState("");
  const queryStringTimeout = useRef<NodeJS.Timeout | null>(null);

  const handleDownload = async (item: Item) => {
    // Temporary solution, waiting for a proper download_url attribute.
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = item.url!;
    a.download = item.filename;
    document.body.appendChild(a);
    a.click();
  };

  const { data: queryData, isLoading } = useItems(
    { title: queryString },
    { enabled: !!queryString }
  );

  const onFilter = (query: string) => {
    setInputValue(query);

    if (queryStringTimeout.current) {
      clearTimeout(queryStringTimeout.current);
    }

    queryStringTimeout.current = setTimeout(
      () => {
        setQueryString(query);
      },
      query.length > 0 ? 300 : 0
    );
  };

  const quickSearchItems: QuickSearchData<Item> = useMemo(() => {
    const items = queryData ?? [];
    return {
      groupName: items.length > 0 ? t("explorer.search.groupName") : "",
      emptyString: t("explorer.search.empty"),
      showWhenEmpty: true,
      elements: items,
    };
  }, [queryData, t]);

  console.log(quickSearchItems);

  const showEmpty = queryString.length === 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size={ModalSize.LARGE}
      title={t("explorer.search.title")}
    >
      <QuickSearch
        placeholder="Search"
        inputValue={inputValue}
        loading={isLoading}
        onFilter={onFilter}
      >
        <div className="explorer__search__modal__items">
          {queryString.length > 0 && (
            <QuickSearchGroup
              group={quickSearchItems}
              onSelect={(element) => {
                if (element.type === ItemType.FOLDER) {
                  router.push(`/explorer/items/${element.id}`);
                } else {
                  handleDownload(element);
                }
                onClose();
              }}
              renderElement={(element) => (
                <QuickSearchItemTemplate
                  left={<SearchModalItem item={element} />}
                  right={
                    <span className="material-icons">keyboard_return</span>
                  }
                />
              )}
            />
          )}
          {showEmpty && (
            <div className="explorer__search__modal__empty">
              <img src={emptySearch.src} alt="empty" />
            </div>
          )}
        </div>
      </QuickSearch>
    </Modal>
  );
};

export const SearchModalItem = ({ item }: { item: Item }) => {
  const ref = useRef<HTMLSpanElement>(null);
  const [isOverflown, setIsOverflown] = useState(false);
  const renderTitle = () => {
    // We need to have the element holding the ref nested because the Tooltip component
    // seems to make the top-most children ref null.
    return (
      <div style={{ display: "flex", overflow: "hidden" }}>
        <span className="explorer__grid__item__name__text" ref={ref}>
          {item.title}
        </span>
      </div>
    );
  };

  useEffect(() => {
    const checkOverflow = () => {
      const element = ref.current;
      // Should always be defined, but just in case.
      if (element) {
        setIsOverflown(element.scrollWidth > element.clientWidth);
      }
    };
    checkOverflow();

    window.addEventListener("resize", checkOverflow);
    return () => {
      window.removeEventListener("resize", checkOverflow);
    };
  }, [item.title]);

  return (
    <div className="explorer__grid__item__name">
      <ItemIcon key={item.id} item={item} />
      {isOverflown ? (
        <Tooltip content={item.title}>{renderTitle()}</Tooltip>
      ) : (
        renderTitle()
      )}
    </div>
  );
};
