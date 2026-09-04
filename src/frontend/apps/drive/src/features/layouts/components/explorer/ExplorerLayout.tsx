import { useAuth } from "@/features/auth/Auth";
import { useConfig } from "@/features/config/ConfigProvider";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import {
  HelpMenu,
  IconSize,
  MainLayout,
  StorageGaugeButton,
  StorageGaugeInformation,
  useResponsive,
  Button,
  Modal,
  ModalProps,
  ModalSize,
  ModalTab,
  Tooltip,
  useModal,
} from "@gouvfr-lasuite/ui-components";
import { HeaderIcon, HeaderRight } from "../header/Header";
import {
  GlobalExplorerProvider,
  NavigationEvent,
  useGlobalExplorer,
} from "@/features/explorer/components/GlobalExplorerContext";
import { ExplorerRightPanelContent } from "@/features/explorer/components/right-panel/ExplorerRightPanelContent";
import { GlobalLayout } from "../global/GlobalLayout";
import { useRouter } from "next/router";
import { useSyncUserLanguage } from "../../hooks/useSyncUserLanguage";
import { Item } from "@/features/drivers/types";
import { ReleaseNoteAuto } from "@/features/ui/components/release-note";
import {
  formatSizeTo,
  setManualNavigationItemId,
} from "@/features/explorer/utils/utils";
import { ColumnPreferencesProvider } from "@/features/explorer/hooks/useColumnPreferences";
import { EntitlementDisclaimers } from "@/features/entitlement-disclaimers/EntitlementDisclaimers";
import { useEntitlements } from "@/features/entitlement-disclaimers/hooks/useEntitlements";
import { Info, Warning } from "@gouvfr-lasuite/ui-components/icons";
import { useTranslation } from "react-i18next";
import i18n from "@/features/i18n/initI18n";
import { useMemo } from "react";
import { UserProfile } from "@/features/ui/components/user/UserProfile";
import { Gaufre } from "@/features/ui/components/gaufre/Gaufre";
import { useMessagesWidget } from "@/features/feedback/useMessagesWidget";

export const getGlobalExplorerLayout = (page: React.ReactElement) => {
  return <GlobalExplorerLayout>{page}</GlobalExplorerLayout>;
};

export const GlobalExplorerLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  return (
    <GlobalLayout>
      <ColumnPreferencesProvider>
        <ReleaseNoteAuto />
        <EntitlementDisclaimers />
        <ExplorerLayout>{children}</ExplorerLayout>
      </ColumnPreferencesProvider>
    </GlobalLayout>
  );
};

/**
 * This layout is used for the explorer page.
 * It is used to display the explorer tree and the header.
 */
export const ExplorerLayout = ({
  children,
}: {
  children: React.ReactNode;
  isMinimalLayout?: boolean;
}) => {
  const router = useRouter();

  const isMinimalLayout = router.query.minimal === "true";
  const itemId = router.query.id as string;
  const onNavigate = (e: NavigationEvent) => {
    // Only keep "minimal" in the query string so that when navigating, to keep the minimal layout on the next page
    // the minimal layout state is preserved; all other query params are dropped intentionally.
    const { minimal } = router.query;
    const item = e.item as Item;
    const query = minimal ? { minimal } : {};
    // If the itemId is a favorite item, we need to get the favorite items. cf onLoadChildren in GlobalExplorerProvider.tsx
    const id = item.originalId ?? item.id;
    setManualNavigationItemId(id);
    router.push({ pathname: `/explorer/items/${id}`, query });
  };

  useSyncUserLanguage();

  return (
    <GlobalExplorerProvider
      itemId={itemId}
      displayMode="app"
      onNavigate={onNavigate}
    >
      <ExplorerPanelsLayout isMinimalLayout={isMinimalLayout}>
        {children}
      </ExplorerPanelsLayout>
    </GlobalExplorerProvider>
  );
};

export const ExplorerPanelsLayout = ({
  children,
  isMinimalLayout,
}: {
  children: React.ReactNode;
  isMinimalLayout?: boolean;
}) => {
  const {
    rightPanelOpen,
    setRightPanelOpen,
    item,
    rightPanelForcedItem: rightPanelItem,
    isLeftPanelOpen,
    setIsLeftPanelOpen,
  } = useGlobalExplorer();

  const { user } = useAuth();

  return (
    <MainLayout
      enableResize
      rightPanelContent={<ExplorerRightPanelContent item={rightPanelItem} />}
      rightPanelIsOpen={rightPanelOpen}
      onToggleRightPanel={() => setRightPanelOpen(!rightPanelOpen)}
      leftPanelContent={user ? <ExplorerTree /> : undefined}
      leftPanelFooter={<LeftPanelFooter />}
      isLeftPanelOpen={isLeftPanelOpen}
      hideLeftPanelOnDesktop={!user || isMinimalLayout}
      setIsLeftPanelOpen={() => setIsLeftPanelOpen(!isLeftPanelOpen)}
      icon={<HeaderIcon />}
      rightHeaderContent={
        <HeaderRight displaySearch={isMinimalLayout} currentItem={item} />
      }
    >
      {children}
    </MainLayout>
  );
};

export const LeftPanelFooter = () => {
  const { isTablet } = useResponsive();
  const settingsModal = useModal();

  return (
    <>
      {isTablet ? (
        <LeftPanelFooterMobile openSettingsModal={settingsModal.open} />
      ) : (
        <LeftPanelFooterDesktop openSettingsModal={settingsModal.open} />
      )}

      <SettingsModal {...settingsModal} />
    </>
  );
};

type LeftPanelFooterProps = {
  openSettingsModal: () => void;
};

export const LeftPanelFooterMobile = (props: LeftPanelFooterProps) => {
  const { user } = useAuth();
  if (!user) {
    return (
      <div className="c__left-panel__footer__drive">
        <HelpMenuButton />
        <UserProfile />
      </div>
    );
  }
  return (
    <div className="c__left-panel__footer__drive">
      <UserProfile />
      <Gaufre />
      <LeftPanelFooterStorageGauge onClick={props.openSettingsModal} />
      <HelpMenuButton />
    </div>
  );
};

const LeftPanelFooterDesktop = (props: LeftPanelFooterProps) => {
  return (
    <div className="c__left-panel__footer__drive">
      <HelpMenuButton />
      <LeftPanelFooterStorageGauge onClick={props.openSettingsModal} />
    </div>
  );
};

const HelpMenuButton = () => {
  const { config } = useConfig();
  const helpMenuConfig = config?.FRONTEND_HELP_MENU_CONFIG;
  const hasHelpMenu =
    !!helpMenuConfig && Object.keys(helpMenuConfig).length > 0;
  const { showWidget } = useMessagesWidget();

  if (!hasHelpMenu) {
    return null;
  }

  const getOnContactUs = () => {
    if (helpMenuConfig.supportMessagesWidget) {
      return () => showWidget();
    }
    return helpMenuConfig.supportEmail
      ? () => window.open(helpMenuConfig.supportEmail)
      : undefined;
  };

  return (
    <HelpMenu
      documentationUrl={helpMenuConfig.documentationUrl}
      legal={helpMenuConfig.legal}
      onContactUs={getOnContactUs()}
    />
  );
};

const SettingsModal = (props: Pick<ModalProps, "isOpen" | "onClose">) => {
  const { t } = useTranslation();
  const tabs: ModalTab[] = [
    {
      id: "tab1",
      label: i18n.t("settings_modal.tabs.storage.title"),
      title: i18n.t("settings_modal.tabs.storage.title"),
      content: <SettingsModalStorageTab />,
    },
  ];

  return (
    <Modal
      variant="tab"
      size={ModalSize.LARGE}
      sidebarTitle={t("settings_modal.title")}
      tabs={tabs}
      constraints={{ preferredHeight: "500px" }}
      {...props}
    />
  );
};

const SettingsModalStorageTab = () => {
  const { config } = useConfig();
  const storageGauge = useStorageGauge();
  if (!storageGauge) {
    return null;
  }
  const informationLink = config?.FRONTEND_STORAGE_GAUGE_INFORMATION_LINK;
  return (
    <StorageGaugeInformation
      {...storageGauge}
      onMoreInfoClick={
        informationLink
          ? () => window.open(informationLink, "_blank")
          : undefined
      }
    />
  );
};

const LeftPanelFooterStorageGauge = (props: { onClick: () => void }) => {
  const storageGauge = useStorageGauge();
  if (!storageGauge) {
    return null;
  }
  console.log("storageGauge", storageGauge);
  return <StorageGaugeButton {...storageGauge} onClick={props.onClick} />;
};

const useStorageGauge = () => {
  const { data: entitlements } = useEntitlements();
  const { t } = useTranslation();

  const quota = useMemo(() => {
    const quota = entitlements?.quota;
    if (!quota) {
      return null;
    }
    if (quota.state === "default") {
      const usageFormatted = formatSizeTo(quota.usage!, "GB");
      const limitFormatted = formatSizeTo(quota.limit!, "GB");
      return {
        quota: quota,
        used: usageFormatted,
        total: limitFormatted,
      };
    } else if (quota.state === "exceeded_locked") {
      return {
        quota: quota,
        used: 0,
        total: 0,
        locked: true,
        // For button gauge.
        lockedContent: (
          <span className="c__storage-gauge__locked-content">
            <Warning size={IconSize.SMALL} />{" "}
            {t(
              `quota.gauge.exceeded_locked.reason.${quota.reason}.description`,
            )}
          </span>
        ),
        // For information gauge.
        title: t("quota.gauge.exceeded_locked.title"),
        label: t("quota.gauge.exceeded_locked.label"),
      };
    } else if (quota.state === "error") {
      return {
        quota: quota,
        used: 0,
        total: 0,
        locked: true,
        // For button gauge.
        lockedContent: (
          <Tooltip
            content={t("quota.gauge.error.tooltip", { error: quota.error })}
          >
            <span className="c__storage-gauge__locked-content">
              <Warning size={IconSize.SMALL} /> {t("quota.gauge.error.title")}
            </span>
          </Tooltip>
        ),
        // For information gauge.
        title: t("quota.gauge.error.title"),
        label: t("quota.gauge.error.label"),
        labelChildren: (
          <Tooltip
            content={t("quota.gauge.error.tooltip", { error: quota.error })}
          >
            <Button
              icon={<Info size={IconSize.SMALL} />}
              size="nano"
              color="neutral"
              variant="tertiary"
            />
          </Tooltip>
        ),
      };
    }
    return null;
  }, [entitlements, t]);

  return quota;
};
