import { Button } from "@gouvfr-lasuite/cunningham-react";
import { UserRow } from "@gouvfr-lasuite/ui-kit";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AccessRequest } from "@/features/drivers/types";
import {
  useItemAccessRequests,
} from "@/features/explorer/hooks/useQueries";
import {
  useMutationUpdateAccessRequest,
} from "@/features/explorer/hooks/useMutationsAccesses";

type AccessRequestsSectionProps = {
  itemId: string;
  canManageAccesses: boolean;
};

export const AccessRequestsSection = ({
  itemId,
  canManageAccesses,
}: AccessRequestsSectionProps) => {
  const { t } = useTranslation();
  const { data } = useItemAccessRequests(itemId);
  const { mutate: updateAccessRequest, isPending } =
    useMutationUpdateAccessRequest();
  const [processingId, setProcessingId] = useState<string>();

  if (!canManageAccesses) {
    return null;
  }

  const pendingRequests = (data?.results ?? []).filter(
    (request: AccessRequest) => request.status === "pending",
  );

  if (pendingRequests.length === 0) {
    return null;
  }

  const handleAnswer = (request: AccessRequest, status: "accepted" | "refused") => {
    setProcessingId(request.id);
    updateAccessRequest(
      {
        itemId,
        accessRequestId: request.id,
        status,
      },
      {
        onSettled: () => setProcessingId(undefined),
      },
    );
  };

  return (
    <div className="workspace-share-modal__access-requests">
      <p className="workspace-share-modal__access-requests__title">
        {t("share_modal.access_requests.title")}
      </p>
      <ul className="workspace-share-modal__access-requests__list">
        {pendingRequests.map((request) => (
          <li
            key={request.id}
            className="workspace-share-modal__access-requests__item"
          >
            <div className="workspace-share-modal__access-requests__item__info">
              <UserRow fullName={request.requester.full_name} />
              {request.message && (
                <p className="workspace-share-modal__access-requests__item__message">
                  {request.message}
                </p>
              )}
            </div>
            <div className="workspace-share-modal__access-requests__item__actions">
              <Button
                variant="bordered"
                size="small"
                disabled={isPending && processingId === request.id}
                onClick={() => handleAnswer(request, "accepted")}
              >
                {t("share_modal.access_requests.accept")}
              </Button>
              <Button
                variant="ghost"
                size="small"
                color="error"
                disabled={isPending && processingId === request.id}
                onClick={() => handleAnswer(request, "refused")}
              >
                {t("share_modal.access_requests.refuse")}
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
