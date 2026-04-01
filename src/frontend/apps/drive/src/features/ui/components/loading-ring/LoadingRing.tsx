type LoadingRingVariant = "neutral" | "brand";
type LoadingRingSize = "sm" | "md" | "lg" | "xl";

interface LoadingRingProps {
  size?: LoadingRingSize;
  variant?: LoadingRingVariant;
}

export const LoadingRing = ({
  size = "md",
  variant = "neutral",
}: LoadingRingProps) => {
  return (
    <div
      className={`drive-loading-ring drive-loading-ring--${size} drive-loading-ring--${variant}`}
    />
  );
};
