import { IconProps as BaseIconProps, IconSize, iconSizeMap } from "@gouvfr-lasuite/ui-kit";

export type IconProps = Partial<BaseIconProps>;

export const IconSvg = (
  props: React.SVGProps<SVGSVGElement> & IconProps,
) => {
  const size = iconSizeMap[props.size as IconSize] || 24;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      {props.children}
    </svg>
  );
};
