import { Explorer } from "@/features/explorer/components/Explorer";
import { ExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useRouter } from "next/router";

export default function ItemPage() {
  const router = useRouter();
  console.log("ItemPage");
  return <Explorer itemId={router.query.id as string} displayMode="app" />;
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <ExplorerLayout>{page}</ExplorerLayout>
    </GlobalLayout>
  );
};
