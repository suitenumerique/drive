import { Explorer } from "@/features/explorer/components/Explorer";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useRouter } from "next/router";
import {
  ExplorerProvider,
  NavigationEvent,
  useExplorer,
} from "@/features/explorer/components/ExplorerContext";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
import { getDriver } from "@/features/config/Config";
import { Button, Loader } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { ItemType, LinkReach } from "@/features/drivers/types";
import { LinkRole } from "@/features/drivers/types";
import { useSearchParams } from "next/navigation";
import { useMutationCreateFile } from "@/features/explorer/hooks/useMutations";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import { fetchAPI } from "@/features/api/fetchApi";
import { Spinner } from "@gouvfr-lasuite/ui-kit";

export enum ClientMessageType {
  // Picker.
  ITEMS_SELECTED = "ITEMS_SELECTED",
  // Saver
  SAVER_READY = "SAVER_READY",
  SAVER_PAYLOAD = "SAVER_PAYLOAD",
  ITEM_SAVED = "ITEM_SAVED",
}

export interface SDKRelayEvent {
  type: string;
  data: any;
}

interface FileSavePayload {
  title: string;
  object: File;
}

interface SaverPayload {
  files: FileSavePayload[];
}

/**
 * This route is gonna be used later for SKD integration as iframe.
 */
export default function ItemPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});

  const token = useMemo(() => {
    return sessionStorage.getItem("sdk_token");
  }, []);

  console.log("token", token);

  const onNavigate = (e: NavigationEvent) => {
    router.push(`/sdk/explorer/items/${e.item.id}`);
  };

  const { data: children } = useQuery({
    queryKey: [
      "items",
      itemId,
      "children",
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ],
    queryFn: () => getDriver().getChildren(itemId, filters),
  });

  if (!token) {
    return <div>No token</div>;
  }

  return (
    <ExplorerProvider itemId={itemId} displayMode="sdk" onNavigate={onNavigate}>
      <div className="explorer__sdk__header">
        {t("sdk.explorer.picker_caption")}
      </div>
      <Explorer
        childrenItems={children}
        filters={filters}
        onFiltersChange={setFilters}
        canSelect={(item) => item.type === ItemType.FILE}
        disableAreaSelection={true}
        disableItemDragAndDrop={true}
      />
      {mode === "save" ? (
        <SaveFooter token={token} />
      ) : (
        <PickerFooter token={token} />
      )}
      {/* The breadcrumbs relies on the tree to be rendered with the cache mecanism. */}
      <div style={{ display: "none" }}>
        <ExplorerTree />
      </div>
    </ExplorerProvider>
  );
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};

class SDKRelayManager {
  static async registerEvent(token: string, event: SDKRelayEvent) {
    return await fetchAPI(`sdk-relay/events/`, {
      method: "POST",
      body: JSON.stringify({
        token,
        event,
      }),
    });
  }
}

const PickerFooter = ({ token }: { token: string }) => {
  const { t } = useTranslation();

  const { selectedItems } = useExplorer();
  const driver = getDriver();

  const [waitForClosing, setWaitForClosing] = useState(false);

  const onChoose = async () => {
    const promises = selectedItems.map((item) => {
      return driver.updateItem({
        id: item.id,
        link_reach: LinkReach.PUBLIC,
        link_role: LinkRole.READER,
      });
    });

    await Promise.all(promises);

    const response = await SDKRelayManager.registerEvent(token, {
      type: ClientMessageType.ITEMS_SELECTED,
      data: {
        items: selectedItems,
      },
    });
    console.log("response", response);
    setWaitForClosing(true);
  };

  const onCancel = () => {
    window.close();
  };

  return (
    <div className="explorer__footer">
      <div className="explorer__footer__caption">
        {t("sdk.explorer.picker_label", {
          count: selectedItems.length,
        })}
      </div>
      <div className="explorer__footer__actions">
        <Button
          color="primary-text"
          onClick={onCancel}
          disabled={waitForClosing}
        >
          {t("sdk.explorer.cancel")}
        </Button>
        <Button
          onClick={onChoose}
          disabled={waitForClosing}
          icon={waitForClosing ? <Spinner size="sm" /> : undefined}
        >
          {t("sdk.explorer.choose")}
        </Button>
      </div>
    </div>
  );
};

const SaveFooter = ({ token }: { token: string }) => {
  const { t } = useTranslation();
  const [payload, setPayload] = useState<SaverPayload | null>(null);
  const createFile = useMutationCreateFile();
  const { itemId } = useExplorer();

  useEffect(() => {
    window.opener.postMessage(
      {
        type: ClientMessageType.SAVER_READY,
      },
      "*"
    );

    const onMessage = (event: MessageEvent) => {
      const { type, data } = event.data;

      if (type === ClientMessageType.SAVER_PAYLOAD) {
        console.log("payload", data);
        // setInterval(() => {
        //   console.log("payload", data);
        // }, 1000);
        setPayload(data);
      }
    };

    window.addEventListener("message", onMessage);

    return () => {
      window.removeEventListener("message", onMessage);
    };
  }, []);

  const onSave = async () => {
    if (!payload) {
      return;
    }
    const promises = [];
    for (const file of payload.files) {
      promises.push(
        () =>
          new Promise<void>((resolve) => {
            createFile.mutate(
              {
                filename: file.title,
                file: file.object,
                parentId: itemId,
              },
              {
                onError: () => {
                  // TODO
                },
                onSettled: () => {
                  resolve();
                },
              }
            );
          })
      );
    }
    for (const promise of promises) {
      await promise();
    }
    window.opener.postMessage(
      {
        type: ClientMessageType.ITEM_SAVED,
        data: {
          items: payload.files,
        },
      },
      "*"
    );
  };

  return (
    <div className="explorer__footer">
      <div>
        <span>{t("sdk.explorer.save_label")} </span>
        {payload?.files.map((file) => (
          <span style={{ fontWeight: "bold" }} key={file.title}>
            {file.title}
          </span>
        ))}
      </div>
      <Button onClick={onSave}>{t("sdk.explorer.save")}</Button>
    </div>
  );
};
