import { Explorer } from "@/features/explorer/components/Explorer";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { DefaultLayout } from "@/features/layouts/components/default/DefaultLayout";
import { useRouter } from "next/router";
import { ExplorerProvider } from "@/features/explorer/components/ExplorerContext";

/**
 * This route is gonna be used later for SKD integration as iframe.
 */
export default function ItemPage() {
  const router = useRouter();
  return (
    <ExplorerProvider itemId={router.query.id as string} displayMode="sdk">
      <Explorer />
    </ExplorerProvider>
  );
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <DefaultLayout>{page}</DefaultLayout>
    </GlobalLayout>
  );
};
