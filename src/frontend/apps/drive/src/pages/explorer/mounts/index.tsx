import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import Link from "next/link";
import { getDriver } from "@/features/config/Config";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { MOUNT_CAPABILITY_KEYS } from "@/features/mounts/constants";

export default function MountsPage() {
  const { t } = useTranslation();

  const {
    data: mounts,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["mounts", "discovery"],
    refetchOnWindowFocus: false,
    queryFn: () => getDriver().getMountsDiscovery(),
  });

  if (isLoading) {
    return <div>{t("explorer.mounts.loading")}</div>;
  }

  if (isError || !mounts) {
    return (
      <div>
        <div>{t("explorer.mounts.error")}</div>
        <Button variant="tertiary" onClick={() => refetch()}>
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  return (
    <div>
      <h1>{t("explorer.mounts.title")}</h1>
      {mounts.length === 0 ? (
        <div>{t("explorer.mounts.empty")}</div>
      ) : (
        <div>
          {mounts.map((mount) => (
            <div key={mount.mount_id}>
              <h2>{mount.display_name}</h2>
              <div>
                {t("explorer.mounts.provider")}: {mount.provider}
              </div>
              <div>
                <Link href={`/explorer/mounts/${mount.mount_id}`}>
                  {t("explorer.mounts.browse")}
                </Link>
              </div>
              <ul>
                {MOUNT_CAPABILITY_KEYS.map((key) => {
                  const supported = Boolean(mount.capabilities?.[key]);
                  return (
                    <li key={key}>
                      {t(`explorer.mounts.capabilities.${key}`)}:{" "}
                      {supported
                        ? t("explorer.mounts.capability.available")
                        : t("explorer.mounts.capability.unavailable")}{" "}
                      {!supported && (
                        <span>({t("common.contact_admin")})</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

MountsPage.getLayout = getGlobalExplorerLayout;
