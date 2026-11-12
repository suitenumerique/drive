import { formatPageTitle } from "@/features/layouts/utils/pageTitle";
import { getSimpleLayout } from "@/features/layouts/components/simple/SimpleLayout";
import { errorToCode } from "@/features/api/APIError";
import { fetchAPI } from "@/features/api/fetchApi";
import { getDriver } from "@/features/config/Config";
import { FilePreview, FilePreviewType } from "@gouvfr-lasuite/ui-components";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

// Matches any item URL shape and captures the UUID:
//   /explorer/items/<uuid>          (folder)
//   /explorer/items/files/<uuid>    (file preview)
//   /wopi/<uuid>                    (office editor)
const ITEM_URL_PATTERN =
  /^\/(?:explorer\/items\/files\/|explorer\/items\/|wopi\/)([0-9a-f-]{36})/;

export const itemIdFromFrom = (from?: string | string[]): string | null => {
  if (!from) return null;
  const url = Array.isArray(from) ? from[0] : from;
  try {
    const match = ITEM_URL_PATTERN.exec(decodeURIComponent(url));
    return match ? match[1] : null;
  } catch {
    return null;
  }
};

export default function UnauthorizedPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const from = router.query.from;
  const itemId = itemIdFromFrom(from);

  const [accessRequested, setAccessRequested] = useState(false);

  // Build the redirect from itemId (a validated UUID) + a static prefix.
  // `from` is only used as a condition, never in the redirect URL,
  // so no user-controlled value reaches router.replace.
  const redirectIfAccessible = useCallback(async () => {
    if (!itemId) return;
    try {
      await fetchAPI(`items/${itemId}/`, undefined, { redirectOn40x: false });
      const raw = Array.isArray(from) ? from[0] : (from as string);
      const decoded = decodeURIComponent(raw ?? "");
      let safePath: string | undefined;
      if (decoded.startsWith("/explorer/items/files/")) {
        safePath = `/explorer/items/files/${itemId}`;
      } else if (decoded.startsWith("/wopi/")) {
        safePath = `/wopi/${itemId}`;
      } else if (decoded.startsWith("/explorer/items/")) {
        safePath = `/explorer/items/${itemId}`;
      }
      if (safePath !== undefined) void router.replace(safePath);
    } catch {
      // item not yet accessible, stay on this page
    }
  }, [itemId, from, router]);

  // If the item becomes accessible (e.g. access was granted), redirect to it.
  // redirectOn40x is disabled to avoid an infinite redirect loop: a 403 here
  // means the user still has no access, so we simply stay on this page.
  useEffect(() => {
    void redirectIfAccessible();
  }, [redirectIfAccessible]);

  // Local mutation without a generic error toast: on the 403 page, any
  // unexpected failure (e.g. the user was just granted access and the
  // ask-for-access endpoint rejects) means we should redirect, not toast.
  const { mutate: createAskForAccess } = useMutation({
    meta: { noGlobalError: true },
    mutationFn: (id: string) => getDriver().createAskForAccess({ itemId: id }),
    onSuccess: () => setAccessRequested(true),
    onError: (error) => {
      if (errorToCode(error) === "already_requested") {
        setAccessRequested(true);
        return;
      }
      void redirectIfAccessible();
    },
  });

  const handleRequestAccess = () => {
    if (!itemId) return;
    createAskForAccess(itemId);
  };

  const file: FilePreviewType = useMemo(
    () => ({
      id: itemId ?? "403",
      // FilePreview owns document.title via useEffect([isOpen, openedFile]).
      // Give it the formatted title so the tab title is correct from the start.
      title: formatPageTitle(t("403.title"), t("app_title")),
      mimetype: "",
      size: 0,
      url: "",
      url_preview: "",
      isFolderAccessDenied: true,
    }),
    [itemId, t],
  );

  return (
    <div className="drive-403-preview">
      <FilePreview
        isOpen={true}
        files={[file]}
        openedFileId={file.id}
        onClose={() => void router.push("/")}
        onRequestAccess={
          itemId && !accessRequested ? handleRequestAccess : undefined
        }
      />
    </div>
  );
}

UnauthorizedPage.getLayout = getSimpleLayout;
