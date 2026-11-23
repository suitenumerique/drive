import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useInfiniteChildren } from "@/features/explorer/hooks/useInfiniteChildren";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { isLink, isWebUrl } from "@/features/drivers/utils";
import { Item } from "@/features/drivers/types";
import { getItemTitle } from "@/features/explorer/utils/utils";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import linkIcon from "@/assets/files/icons/mime-link.svg";
import { Button, Icon } from "@gouvfr-lasuite/ui-components";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { useState, useMemo } from "react";

export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});

  // Shared item URLs all land here, links included: know the type before
  // loading any children, a link has none.
  const {
    data: item,
    isLoading: isItemLoading,
    isError: isItemError,
  } = useItem(itemId, {
    enabled: !!itemId,
  });
  const currentItem = item?.id === itemId ? item : undefined;
  const isLinkItem = !!currentItem && isLink(currentItem);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isPending,
    isPlaceholderData,
  } = useInfiniteChildren(itemId, filters, !!currentItem && !isLinkItem);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  if (!currentItem && isItemLoading) {
    return <SpinnerPage />;
  }

  if (isLinkItem) {
    return <LinkInterstitial item={currentItem} />;
  }

  return (
    <AppExplorer
      viewConfigKey="folder"
      navigationId={itemId}
      onComputedFiltersChange={setFilters}
      childrenItems={itemChildren}
      hasNextPage={hasNextPage}
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      // The children query waits for the item: no children yet is a load, not
      // an empty folder, unless the item itself failed to load.
      isLoading={(isPending && !isItemError) || isPlaceholderData}
    />
  );
}

// A link is never followed without a click: the page shows where it leads.
const LinkInterstitial = ({ item }: { item: Item }) => {
  const { t } = useTranslation();

  // A link under a trashed folder keeps a null deleted_at of its own.
  if (item.deleted_at || item.ancestors_deleted_at) {
    return (
      <GenericDisclaimer
        message={t("explorer.trash.navigate.modal_link.title")}
        imageSrc={linkIcon.src}
      >
        <p>{t("explorer.trash.navigate.modal_link.description")}</p>
      </GenericDisclaimer>
    );
  }

  return (
    <GenericDisclaimer message={getItemTitle(item)} imageSrc={linkIcon.src}>
      <p className="clr-greyscale-600">{item.link_url}</p>
      {isWebUrl(item.link_url) && (
        <Button
          href={item.link_url}
          target="_blank"
          rel="noopener noreferrer"
          icon={<Icon name="open_in_new" />}
        >
          {t("explorer.link.open")}
        </Button>
      )}
    </GenericDisclaimer>
  );
};

ItemPage.getLayout = getGlobalExplorerLayout;
