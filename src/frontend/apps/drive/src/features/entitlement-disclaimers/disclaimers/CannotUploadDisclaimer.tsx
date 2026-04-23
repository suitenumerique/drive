import {
  EntitlementCanUploadReasons,
  Entitlements,
} from "@/features/drivers/Driver";
import { EntitlementDisclaimer } from "../types";
import { ApiConfig } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import i18n from "@/features/i18n/initI18n";

/**
 * Show a disclaimer if the user cannot upload.
 * As a reminder can_access is always true, so we need to check can_upload.
 * can_upload can be false for multiple reasons:
 * - The user is not activated.
 * - The user is not attached to an organization.
 * - The storage is full.
 *
 * We only show the disclaimer if the user is not activated or not attached to an organization.
 * So we can inform the user that he needs to contact his administrator to activate his account or
 * to attach his account to an organization.
 */
const CannotUploadDisclaimer: EntitlementDisclaimer<"cannot_upload"> = {
  name: "cannot_upload",
  show: (entitlements) => {
    if (entitlements.can_upload.result) {
      return false;
    }

    return (
      [
        EntitlementCanUploadReasons.NOT_ACTIVATED,
        EntitlementCanUploadReasons.NO_ORGANIZATION,
      ] as string[]
    ).includes(entitlements.can_upload.reason || "");
  },
  render: (config, entitlements) => {
    return {
      title: i18n.t("entitlements.disclaimers.cannot_upload.title"),
      description: <Content config={config} entitlements={entitlements} />,
    };
  },
};

const Content = ({
  config,
  entitlements,
}: {
  config: NonNullable<
    ApiConfig["FRONTEND_ENTITLEMENTS_DISCLAIMERS"]
  >["cannot_upload"];
  entitlements: Entitlements;
}) => {
  const { t } = useTranslation();
  return (
    <div>
      {entitlements.can_upload.reason ===
        EntitlementCanUploadReasons.NOT_ACTIVATED && (
        <p>
          {t(
            "entitlements.disclaimers.cannot_upload.not_activated.description",
          )}
        </p>
      )}
      {entitlements.can_upload.reason ===
        EntitlementCanUploadReasons.NO_ORGANIZATION && (
        <p>
          {t(
            "entitlements.disclaimers.cannot_upload.no_organization.description",
          )}
        </p>
      )}
      {config?.showPotentialOperators &&
        (entitlements.context?.potentialOperators?.length ?? 0) > 0 && (
          <div>
            {t(
              "entitlements.disclaimers.cannot_upload.potential_operators.description",
            )}
            <ul>
              {entitlements.context.potentialOperators?.map((operator) => {
                return (
                  <li key={operator.id}>
                    <strong>{operator.name}</strong>
                    {operator.signupUrl && (
                      <>
                        {" "}
                        (
                        <a
                          href={operator.signupUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {t(
                            "entitlements.disclaimers.cannot_upload.potential_operators.link",
                          )}
                        </a>
                        )
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
    </div>
  );
};

export default CannotUploadDisclaimer;
