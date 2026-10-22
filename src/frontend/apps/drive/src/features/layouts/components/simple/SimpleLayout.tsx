import { MainLayout } from "@gouvfr-lasuite/ui-components";
import { GlobalLayout } from "../global/GlobalLayout";
import { HeaderRight } from "../header/Header";
import { Toaster } from "@/features/ui/components/toaster/Toaster";
import { LeftPanelFooter } from "../explorer/ExplorerLayout";
import { useHeaderBannerAnnouncement } from "@/features/announcements/useHeaderBannerAnnouncement";

export const getSimpleLayout = (page: React.ReactElement) => {
  return <SimpleLayout>{page}</SimpleLayout>;
};

/**
 * This layout is used for the simple pages.
 * It is used to display the header and provide
 * Auth context to the children.
 */
export const SimpleLayout = ({ children }: { children: React.ReactNode }) => {
  const topBanner = useHeaderBannerAnnouncement();

  return (
    <div>
      <GlobalLayout>
        <MainLayout
          enableResize
          topBanner={topBanner}
          hideLeftPanelOnDesktop={true}
          leftPanelFooter={<LeftPanelFooter />}
          rightHeaderContent={<HeaderRight />}
        >
          {children}
          <Toaster />
        </MainLayout>
      </GlobalLayout>
    </div>
  );
};
