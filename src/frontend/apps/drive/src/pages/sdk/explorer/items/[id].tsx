import { Explorer } from "@/features/explorer/components/Explorer";
import { SdkLayout } from "@/features/layouts/components/sdk/SdkLayout";
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
