import { getDriver } from "@/features/config/Config";
import { errorToCode } from "@/features/api/APIError";
import { EntitlementCanUploadReasons } from "@/features/drivers/Driver";
import { getCannotUploadReasonDescription } from "@/features/entitlement-disclaimers/disclaimers/CannotUploadDisclaimer";

export const getEntitlements = async () => {
  const driver = getDriver();
  return driver.getEntitlements();
};

/**
 * The quota gates (upload, move, duplicate) expose the can_upload reason as the
 * API error code: map it back to its localized description when known.
 */
export const getCanUploadErrorDescription = (
  error: unknown,
  translate?: (key: string) => string,
): string | undefined => {
  const code = errorToCode(error);
  if (
    code &&
    Object.values(EntitlementCanUploadReasons).includes(
      code as EntitlementCanUploadReasons,
    )
  ) {
    if (translate) {
      return translate(code);
    }
    return getCannotUploadReasonDescription(
      code as EntitlementCanUploadReasons,
    );
  }
  return undefined;
};
