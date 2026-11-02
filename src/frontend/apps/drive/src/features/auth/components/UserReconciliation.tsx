import { Icon } from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";

import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";

import {
  UserReconciliationType,
  useUserReconciliationQuery,
} from "../hooks/useUserReconciliations";

interface UserReconciliationProps {
  userType: UserReconciliationType;
  reconciliationId: string;
}

export const UserReconciliation = ({
  userType,
  reconciliationId,
}: UserReconciliationProps) => {
  const { t } = useTranslation();
  const { isPending, isError } = useUserReconciliationQuery(
    userType,
    reconciliationId,
  );

  if (isPending) {
    return <SpinnerPage />;
  }

  return (
    <div className="drive__user-reconciliation">
      <Icon name={isError ? "error" : "mark_email_read"} />
      <p>
        {isError
          ? t("user_reconciliation.error")
          : t("user_reconciliation.success")}
      </p>
    </div>
  );
};
