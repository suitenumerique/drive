type SpinnerVariant = "neutral" | "brand";
type SpinnerSize = "sm" | "md" | "lg" | "xl";

interface SpinnerProps {
  size?: SpinnerSize;
  variant?: SpinnerVariant;
}

export const Spinner = ({ size = "md", variant = "neutral" }: SpinnerProps) => {
  return (
    <div
      className={`drive-spinner drive-spinner--${size} drive-spinner--${variant}`}
    />
  );
};
