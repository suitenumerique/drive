import { ExplorerLayout } from "@/components/layouts/explorer/ExplorerLayout";
import { GlobalLayout } from "@/components/layouts/global/GlobalLayout";

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
