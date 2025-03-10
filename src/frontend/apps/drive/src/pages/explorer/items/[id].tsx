import { Explorer } from "@/features/explorer/components/Explorer";
import { ExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";

export default function ItemPage() {
  return <Explorer />;
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <ExplorerLayout>{page}</ExplorerLayout>
    </GlobalLayout>
  );
};
