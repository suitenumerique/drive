import { Auth } from "@/features/auth/Auth";
import {
  ExplorerProvider,
  NavigationEvent,
} from "@/features/explorer/components/ExplorerContext";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import { PickerFooter } from "@/features/sdk/SdkPickerFooter";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

export const getSdkLayout = (page: React.ReactElement) => {
  return <SdkLayout>{page}</SdkLayout>;
};

export const getSdkPickerLayout = (page: React.ReactElement) => {
  return <SdkSaveLayout>{page}</SdkSaveLayout>;
};

export const SdkSaveLayout = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(sessionStorage.getItem("sdk_token"));
  }, [token]);

  if (!token) {
    return null;
  }

  return (
    <SdkLayout>
      {children}
      <PickerFooter token={token} />
      {/* The breadcrumbs relies on the tree to be rendered with the cache mecanism. */}
      <div style={{ display: "none" }}>
        <ExplorerTree />
      </div>
    </SdkLayout>
  );
};

export const SdkLayout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const itemId = router.query.id as string;
  const { t } = useTranslation();

  const onNavigate = (e: NavigationEvent) => {
    router.push(`/sdk/explorer/items/${e.item.id}`);
  };

  return (
    <Auth>
      <ExplorerProvider
        itemId={itemId}
        displayMode="sdk"
        onNavigate={onNavigate}
      >
        <div className="explorer__sdk__header">
          {t("sdk.explorer.picker_caption")}
        </div>
        {children}
      </ExplorerProvider>
    </Auth>
  );
};
