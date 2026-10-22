import { MainLayout } from "@gouvfr-lasuite/ui-components";
import { GlobalLayout } from "../global/GlobalLayout";
import { HeaderRight } from "../header/Header";
import { Toaster } from "@/features/ui/components/toaster/Toaster";
import { LeftPanelFooter } from "../explorer/ExplorerLayout";
import { useConfigHeaderBanner } from "@/features/header-banner/useConfigHeaderBanner";

export const getSimpleLayout = (page: React.ReactElement) => {
  return <SimpleLayout>{page}</SimpleLayout>;
};

/**
 * This layout is used for the simple pages.
 * It is used to display the header and provide
 * Auth context to the children.
 */
export const SimpleLayout = ({ children }: { children: React.ReactNode }) => {
  const topBanner = useConfigHeaderBanner();

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
