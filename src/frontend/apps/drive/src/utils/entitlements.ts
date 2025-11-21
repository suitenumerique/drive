import { getDriver } from "@/features/config/Config";

export const getEntitlements = async () => {
  const driver = getDriver();
  return driver.getEntitlements();
};
