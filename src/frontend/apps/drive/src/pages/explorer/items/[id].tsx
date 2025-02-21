import { Explorer } from "@/components/explorer/Explorer";
import { ExplorerLayout } from "@/components/layouts/explorer/ExplorerLayout";
import { GlobalLayout } from "@/components/layouts/global/GlobalLayout";
import { useRouter } from "next/router";

export default function ItemPage() {
  const router = useRouter();
  return <Explorer itemId={router.query.id as string} />;
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <ExplorerLayout>{page}</ExplorerLayout>
    </GlobalLayout>
  );
};
