import { getSimpleLayout } from "@/features/layouts/components/simple/SimpleLayout";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { errorToCode } from "@/features/api/APIError";
import { fetchAPI } from "@/features/api/fetchApi";
import { useMutationCreateAskForAccess } from "@/features/explorer/hooks/useMutationsAccesses";
import { Icon, Button } from "@gouvfr-lasuite/ui-components";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

// Matches any item URL shape and captures the UUID:
//   /explorer/items/<uuid>          (folder)
//   /explorer/items/files/<uuid>    (file preview)
//   /wopi/<uuid>                    (office editor)
const ITEM_URL_PATTERN =
  /^\/(?:explorer\/items\/files\/|explorer\/items\/|wopi\/)([0-9a-f-]{36})/;

const itemIdFromFrom = (from?: string | string[]): string | null => {
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

  const [requestSent, setRequestSent] = useState(false);
  const [alreadyRequested, setAlreadyRequested] = useState(false);

  const { mutate: createAskForAccess, isPending } =
    useMutationCreateAskForAccess();

  // If the item becomes accessible (e.g. access was granted), redirect to it.
  // redirectOn40x is disabled to avoid an infinite redirect loop: a 403 here
  // means the user still has no access, so we simply stay on this page.
  useEffect(() => {
    if (!itemId) return;
    fetchAPI(`items/${itemId}/`, undefined, { redirectOn40x: false }).then(
      () => {
        try {
          const raw = Array.isArray(from) ? from[0] : (from as string);
          const target = decodeURIComponent(raw ?? "");
          // exec so match[0] contains only the regex-bounded path+UUID,
          // never trailing query params or extra paths from `target`.
          const match = ITEM_URL_PATTERN.exec(target);
          if (match && match[0].startsWith("/")) {
            void router.replace(match[0]);
          }
        } catch {
          // malformed encoding, stay on this page
        }
      },
    ).catch(() => {
      // item not yet accessible, stay on this page
    });
  }, [itemId]);

  const canAskForAccess = Boolean(itemId) && !requestSent && !alreadyRequested;

  const getMessageKey = () => {
    if (requestSent) return "403.ask_for_access.success";
    if (alreadyRequested) return "403.ask_for_access.already_requested";
    return "403.title";
  };
  const message = t(getMessageKey());

  const handleAskForAccess = () => {
    if (!itemId) return;
    createAskForAccess(
      { itemId },
      {
        onSuccess: () => setRequestSent(true),
        onError: (error) => {
          if (errorToCode(error) === "already_requested") {
            setAlreadyRequested(true);
          }
        },
      },
    );
  };

  return (
    <GenericDisclaimer message={message} imageSrc="/assets/403-background.png">
      {canAskForAccess && (
        <Button
          onClick={handleAskForAccess}
          disabled={isPending}
          icon={<Icon name="mail" />}
        >
          {t("403.ask_for_access.button")}
        </Button>
      )}
      <Button href="/" variant={canAskForAccess ? "tertiary" : undefined}>
        <Icon name="home" />
        {t("403.button")}
      </Button>
    </GenericDisclaimer>
  );
}

UnauthorizedPage.getLayout = getSimpleLayout;
