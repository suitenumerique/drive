import { ReactNode } from "react";
import { Entitlements } from "../drivers/Driver";
import { ApiConfig } from "../drivers/types";

type DisclaimersConfig = NonNullable<
  ApiConfig["FRONTEND_ENTITLEMENTS_DISCLAIMERS"]
>;

export type EntitlementDisclaimer<
  Name extends keyof DisclaimersConfig = keyof DisclaimersConfig,
> = {
  name: Name;
  show: (entitlements: Entitlements) => boolean;
  render: (
    config: DisclaimersConfig[Name],
    entitlements: Entitlements,
  ) => {
    title: string;
    description: ReactNode;
  };
};
