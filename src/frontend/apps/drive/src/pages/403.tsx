import { getSimpleLayout } from "@/features/layouts/components/simple/SimpleLayout";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useRouter } from "next/router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useMutationCreateAccessRequest,
} from "@/features/explorer/hooks/useMutationsAccesses";
import { errorToCode } from "@/features/api/APIError";

const ITEM_URL_PATTERN = /\/explorer\/items\/(?:files\/)?([0-9a-f-]{36})/;

export const formatItemIdFromRedirectTo = (
  redirectTo?: string | string[],
): string | null => {
  if (!redirectTo) {
    return null;
  }
  const url = Array.isArray(redirectTo) ? redirectTo[0] : redirectTo;
  try {
    const match = decodeURIComponent(url).match(ITEM_URL_PATTERN);
    return match ? match[1] : null;
  } catch {
    return null;
  }
};

export default function UnauthorizedPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const itemId = formatItemIdFromRedirectTo(router.query.redirect_to);

  const [message, setMessage] = useState("");
  const [requestSent, setRequestSent] = useState(false);
  const [alreadyRequested, setAlreadyRequested] = useState(false);

  const createAccessRequest = useMutationCreateAccessRequest();

  const canAskForAccess = Boolean(itemId) && !requestSent && !alreadyRequested;

  const handleAskForAccess = () => {
    if (!itemId) {
      return;
    }
    createAccessRequest.mutate(
      { itemId, message },
      {
        onSuccess: () => {
          setRequestSent(true);
        },
        onError: (error) => {
          if (errorToCode(error) === "access_request_already_pending") {
            setAlreadyRequested(true);
          }
        },
      },
    );
  };

  return (
    <GenericDisclaimer
      message={
        requestSent
          ? t("403.ask_for_access.success")
          : alreadyRequested
            ? t("403.ask_for_access.already_requested")
            : t("403.ask_for_access.description")
      }
      imageSrc="/assets/403-background.png"
    >
      {canAskForAccess && (
        <>
          <label className="drive__generic-disclaimer__content__label">
            {t("403.ask_for_access.message_label")}
          </label>
          <textarea
            className="drive__generic-disclaimer__content__message"
            rows={4}
            value={message}
            placeholder={t("403.ask_for_access.message_placeholder")}
            onChange={(e) => setMessage(e.target.value)}
          />
          {createAccessRequest.error && !alreadyRequested && (
            <p className="drive__generic-disclaimer__content__error">
              {t("403.ask_for_access.error")}
            </p>
          )}
          <Button
            onClick={handleAskForAccess}
            disabled={createAccessRequest.isPending}
            icon={<Icon name="mail" />}
          >
            {t("403.ask_for_access.button")}
          </Button>
        </>
      )}
      <Button href="/" variant={canAskForAccess ? "tertiary" : undefined}>
        <Icon name="home" />
        {t("403.button")}
      </Button>
    </GenericDisclaimer>
  );
}

UnauthorizedPage.getLayout = getSimpleLayout;
