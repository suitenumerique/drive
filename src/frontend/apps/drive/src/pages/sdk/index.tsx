import { Loader } from "@openfun/cunningham-react";
import { useEffect } from "react";
import { useAuth } from "@/features/auth/Auth";
import { getLastVisitedItem } from "@/features/explorer/utils/utils";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useSearchParams } from "next/navigation";

export default function SDKPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");

  const redirect = async () => {
    const item = await getLastVisitedItem();
    if (item) {
      let url = `/sdk/explorer/items/${item.id}`;
      if (mode) {
        url += `?mode=${mode}`;
      }
      window.location.href = url;
    }
  };

  useEffect(() => {
    if (user) {
      redirect();
    }
  }, [user]);
  return <Loader />;
}

SDKPage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};
