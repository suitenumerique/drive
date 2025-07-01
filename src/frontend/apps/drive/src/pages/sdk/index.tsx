import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { useEffect } from "react";
import { login, useAuth } from "@/features/auth/Auth";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useSearchParams } from "next/navigation";

export default function SDKPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");
  const token = searchParams.get("token");

  const redirect = async () => {
    let url = `/sdk/explorer/workspaces`;
    if (mode) {
      url += `?mode=${mode}`;
    }
    window.location.href = url;
  };

  useEffect(() => {
    if (!token) {
      throw new Error("Token is required");
    }

    sessionStorage.setItem("sdk_token", token);

    if (user) {
      redirect();
    } else {
      const returnTo = window.location.href;
      login(returnTo);
    }
  }, [user]);

  return (
    <div className="sdk__page">
      <Spinner size="xl" />
    </div>
  );
}

SDKPage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};
