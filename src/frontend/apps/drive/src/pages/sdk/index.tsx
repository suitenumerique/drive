import { Loader } from "@openfun/cunningham-react";
import { useEffect } from "react";
import { useAuth } from "@/features/auth/Auth";
import { gotoLastVisitedItem } from "@/features/explorer/utils/utils";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";

export default function SDKPage() {
  const { user } = useAuth();

  useEffect(() => {
    console.log("user", user);
    if (user) {
      gotoLastVisitedItem("/sdk");
    }
  }, [user]);
  return <Loader />;
}

SDKPage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};
