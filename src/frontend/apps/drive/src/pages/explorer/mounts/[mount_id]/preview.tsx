import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { APIError } from "@/features/api/APIError";
import { fetchAPI } from "@/features/api/fetchApi";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";

type PreviewData = {
  objectUrl: string;
  contentType: string;
  apiUrl: string;
};

export default function MountPreviewPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const mountId = String(router.query.mount_id ?? "");
  const path = String(router.query.path ?? "");

  const apiUrl = useMemo(() => {
    if (!mountId || !path) {
      return "";
    }
    const query = new URLSearchParams({ path });
    return `/api/v1.0/mounts/${mountId}/preview/?${query.toString()}`;
  }, [mountId, path]);

  const { data, isLoading, error } = useQuery<PreviewData>({
    queryKey: ["mounts", "preview", mountId, path],
    enabled: Boolean(mountId && path),
    refetchOnWindowFocus: false,
    queryFn: async () => {
      const response = await fetchAPI(
        `mounts/${mountId}/preview/`,
        { params: { path } },
        { redirectOn40x: false },
      );
      const blob = await response.blob();
      const contentType =
        response.headers.get("Content-Type") ?? blob.type ?? "application/octet-stream";
      const objectUrl = URL.createObjectURL(blob);
      return { objectUrl, contentType, apiUrl };
    },
  });

  useEffect(() => {
    if (!data?.objectUrl) {
      return;
    }
    return () => URL.revokeObjectURL(data.objectUrl);
  }, [data?.objectUrl]);

  const apiErrorCode =
    error instanceof APIError ? error.data?.errors?.[0]?.code : null;

  const showNotAvailable =
    apiErrorCode === "mount.preview.disabled" ||
    apiErrorCode === "mount.preview.unavailable" ||
    apiErrorCode === "mount.preview.not_previewable";

  if (!mountId || !path) {
    return (
      <div>
        <div>{t("explorer.mounts.preview_page.missing_params")}</div>
        <Link href="/explorer/mounts">{t("explorer.mounts.title")}</Link>
      </div>
    );
  }

  if (isLoading) {
    return <div>{t("explorer.mounts.preview_page.loading")}</div>;
  }

  if (showNotAvailable) {
    return (
      <div>
        <h1>{t("explorer.mounts.preview_page.title")}</h1>
        <div>{t("explorer.mounts.preview_page.not_available")}</div>
        <div>{t("explorer.mounts.preview_page.next_action")}</div>
        <Button
          variant="tertiary"
          onClick={() =>
            router.push({
              pathname: "/explorer/mounts/[mount_id]",
              query: { mount_id: mountId, path: "/" },
            })
          }
        >
          {t("common.back")}
        </Button>
      </div>
    );
  }

  if (apiErrorCode === "mount.smb.env.auth_failed") {
    return (
      <div>
        <h1>{t("explorer.mounts.preview_page.title")}</h1>
        <div>{t("explorer.mounts.preview_page.access_denied")}</div>
        <Button
          variant="tertiary"
          onClick={() =>
            router.push({
              pathname: "/explorer/mounts/[mount_id]",
              query: { mount_id: mountId, path: "/" },
            })
          }
        >
          {t("common.back")}
        </Button>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <h1>{t("explorer.mounts.preview_page.title")}</h1>
        <div>{t("explorer.mounts.preview_page.error")}</div>
        <Button variant="tertiary" onClick={() => router.reload()}>
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  const isImage = data.contentType.startsWith("image/");

  return (
    <div>
      <h1>{t("explorer.mounts.preview_page.title")}</h1>
      <div>
        <Link href={data.apiUrl} target="_blank" rel="noreferrer">
          {t("explorer.mounts.preview_page.open_new_tab")}
        </Link>
      </div>
      {isImage ? (
        <img
          src={data.objectUrl}
          alt={t("explorer.mounts.preview_page.title")}
          style={{ maxWidth: "100%" }}
        />
      ) : (
        <iframe
          src={data.objectUrl}
          title={t("explorer.mounts.preview_page.title")}
          style={{ width: "100%", height: "70vh", border: 0 }}
        />
      )}
    </div>
  );
}

MountPreviewPage.getLayout = getGlobalExplorerLayout;

