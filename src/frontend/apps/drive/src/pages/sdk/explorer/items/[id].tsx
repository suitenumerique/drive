import { Explorer } from "@/components/explorer/Explorer";
import { ExplorerLayout } from "@/components/layouts/explorer/ExplorerLayout";
import { GlobalLayout } from "@/components/layouts/global/GlobalLayout";
import { SdkLayout } from "@/components/layouts/sdk/SdkLayout";
import { useRouter } from "next/router";

/**
 * This route is gonna be used later for SKD integration as iframe.
 */

export default function ItemPage() {
  const router = useRouter();
  return <Explorer itemId={router.query.id as string} />;
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return <SdkLayout>{page}</SdkLayout>;
};
