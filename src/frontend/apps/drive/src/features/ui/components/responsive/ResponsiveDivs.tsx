export const ResponsiveDivs = () => {
  return (
    <>
      <div id="responsive-tablet"></div>
    </>
  );
};

export const isTablet = () => {
  return (
    document
      .querySelector("#responsive-tablet")
      ?.computedStyleMap()
      .get("display")
      ?.toString() === "block"
  );
};
