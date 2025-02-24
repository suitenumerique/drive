import { ExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";

export default function ExplorerPage() {
  return <div>explorer</div>;
}

ExplorerPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <ExplorerLayout>{page}</ExplorerLayout>
    </GlobalLayout>
  );
};
