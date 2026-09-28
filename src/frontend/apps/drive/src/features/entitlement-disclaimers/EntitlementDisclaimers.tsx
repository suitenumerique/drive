import { EntitlementDisclaimerModal } from "./components/EntitlementDisclaimerModal";
import CannotUploadDisclaimer from "./disclaimers/CannotUploadDisclaimer";
import { EntitlementDisclaimer } from "./types";
import { useEffect, useState } from "react";
import { useEntitlements } from "./hooks/useEntitlements";
import { useConfig } from "../config/ConfigProvider";
import { ApiConfig } from "../drivers/types";

export const storageKey = (name: string) =>
  `entitlement-disclaimer-seen:${name}`;

const DISCLAIMER_REGISTRY = [CannotUploadDisclaimer];

const DISCLAIMER_REGISTRY_MAP = DISCLAIMER_REGISTRY.reduce(
  (acc, disclaimer) => {
    acc[disclaimer.name] = disclaimer;
    return acc;
  },
  {} as Record<
    keyof NonNullable<ApiConfig["FRONTEND_ENTITLEMENTS_DISCLAIMERS"]>,
    EntitlementDisclaimer
  >,
);

export const EntitlementDisclaimers = () => {
  const { config } = useConfig();
  const { data: entitlements } = useEntitlements();
  const [activeDisclaimers, setActiveDisclaimers] =
    useState<EntitlementDisclaimer[]>();

  /**
   * Compute active disclaimers.
   */
  useEffect(() => {
    if (!entitlements) {
      return;
    }
    if (activeDisclaimers !== undefined) {
      return;
    }
    const activeDisclaimers_tmp = [] as EntitlementDisclaimer[];
    Object.entries(DISCLAIMER_REGISTRY_MAP).forEach(([name, disclaimer]) => {
      // Disabled in config?
      if (
        config.FRONTEND_ENTITLEMENTS_DISCLAIMERS?.[
          name as keyof typeof config.FRONTEND_ENTITLEMENTS_DISCLAIMERS
        ]?.enabled !== true
      ) {
        return;
      }
      const show = disclaimer.show(entitlements);
      const key = storageKey(name);
      // Already seen.
      if (localStorage.getItem(key)) {
        if (!show) {
          // Clear seen flag. So on next change, the disclaimer will be shown again.
          localStorage.removeItem(key);
        }
        return;
      }
      // Should not be shown.
      if (!show) {
        return;
      }
      // Should be shown.
      localStorage.setItem(key, "1");
      activeDisclaimers_tmp.push(disclaimer);
    });
    setActiveDisclaimers(activeDisclaimers_tmp);
  }, [entitlements]);

  if (!entitlements) {
    return null;
  }

  return (
    <>
      {activeDisclaimers?.map((disclaimer) => {
        const { title, description } = disclaimer.render(
          config.FRONTEND_ENTITLEMENTS_DISCLAIMERS?.[disclaimer.name],
          entitlements,
        );
        return (
          <EntitlementDisclaimerModal
            key={disclaimer.name}
            title={title}
            description={description}
          />
        );
      })}
    </>
  );
};
