import { resolveGaufreProps } from "../resolveGaufreProps";

const defaults = {
  widgetPath: "https://widgets.example.org/lagaufre.js",
  apiUrl: "https://services.example.org/api/services",
  showMoreLimit: 6,
};

const services = [{ name: "Docs", url: "https://docs.example.org" }];

describe("resolveGaufreProps", () => {
  it("returns the theme defaults when there is no customization", () => {
    expect(resolveGaufreProps(undefined, defaults)).toEqual(defaults);
  });

  it("uses the customized api url and keeps the default widget path", () => {
    expect(
      resolveGaufreProps(
        { apiUrl: "https://launcher.example.org/services.json" },
        defaults,
      ),
    ).toEqual({
      widgetPath: defaults.widgetPath,
      showMoreLimit: defaults.showMoreLimit,
      apiUrl: "https://launcher.example.org/services.json",
    });
  });

  it("uses the customized static services instead of the default api url", () => {
    const props = resolveGaufreProps({ data: { services } }, defaults);

    expect(props).toEqual({
      widgetPath: defaults.widgetPath,
      showMoreLimit: defaults.showMoreLimit,
      data: { services },
    });
    expect(props.apiUrl).toBeUndefined();
  });

  it("lets the customization override the widget path and the limit", () => {
    expect(
      resolveGaufreProps(
        {
          apiUrl: "https://launcher.example.org/services.json",
          widgetPath: "https://launcher.example.org/lagaufre.js",
          showMoreLimit: 9,
        },
        defaults,
      ),
    ).toEqual({
      apiUrl: "https://launcher.example.org/services.json",
      widgetPath: "https://launcher.example.org/lagaufre.js",
      showMoreLimit: 9,
    });
  });
});
