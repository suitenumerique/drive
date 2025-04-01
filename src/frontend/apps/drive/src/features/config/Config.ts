import { StandardDriver } from "../drivers/implementations/StandardDriver";
// import { DummyDriver } from "../drivers/implementations/DummyDriver";

export const getConfig = () => {
  // TODO: Later, be based on URL query params for instance.
  return {
    // driver: new DummyDriver(),
    driver: new StandardDriver(),
  };
};

export const getDriver = () => {
  return getConfig().driver;
};
