import { getSimpleLayout } from "@/features/layouts/components/simple/SimpleLayout";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { errorToCode } from "@/features/api/APIError";
import { useMutationCreateAskForAccess } from "@/features/explorer/hooks/useMutationsAccesses";
import { Icon, Button } from "@gouvfr-lasuite/ui-components";
import { useRouter } from "next/router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

// Matches any item URL shape and captures the UUID:
//   /explorer/items/<uuid>          (folder)
//   /explorer/items/files/<uuid>    (file preview)
//   /wopi/<uuid>                    (office editor)
const ITEM_URL_PATTERN =
  /\/(?:explorer\/items\/files\/|explorer\/items\/|wopi\/)([0-9a-f-]{36})/;

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
  const itemId = itemIdFromFrom(router.query.from);

  const [requestSent, setRequestSent] = useState(false);
  const [alreadyRequested, setAlreadyRequested] = useState(false);

  const { mutate: createAskForAccess, isPending } =
    useMutationCreateAskForAccess();

  const canAskForAccess = Boolean(itemId) && !requestSent && !alreadyRequested;

  const message = requestSent
    ? t("403.ask_for_access.success")
    : alreadyRequested
      ? t("403.ask_for_access.already_requested")
      : t("403.title");

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
