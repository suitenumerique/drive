import { CheckIcon } from "@/features/ui/components/icon/CheckIcon";

interface CircularProgressProps {
  progress: number;
  size?: number;
  strokeWidth?: number;
  primaryColor?: string;
  secondaryColor?: string;
  transitionDuration?: number;
}

export const CircularProgress = ({
  progress,
  primaryColor = "#1a237e",
  secondaryColor = "#f0f0f0",
  transitionDuration = 0.3,
}: CircularProgressProps) => {
  if (progress > 100) {
    progress = 100;
  }

  const strokeWidth = 2;

  // Fixed size of 24px for the component
  const fixedSize = 24;
  // Fixed size of 20px for the circle
  const circleSize = 20;

  // Calculate the radius based on the circle size
  const radius = circleSize / 2;
  const circumference = 2 * Math.PI * radius;

  // Calculate the dash offset based on progress
  const dashOffset = circumference - (progress / 100) * circumference;

  // Determine if we should show the check mark
  const isComplete = progress >= 100;

  return (
    <div
      style={{
        position: "relative",
        width: `${fixedSize}px`,
        height: `${fixedSize}px`,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {!isComplete && (
        <svg
          width={fixedSize}
          height={fixedSize}
          viewBox={`0 0 ${fixedSize} ${fixedSize}`}
          style={{ transform: isComplete ? "rotate(0deg)" : "rotate(-90deg)" }}
        >
          {/* Background circle - centered in the 24x24 container */}
          <circle
            cx={fixedSize / 2}
            cy={fixedSize / 2}
            r={radius}
            fill="none"
            stroke={secondaryColor}
            strokeWidth={strokeWidth}
          />

          {/* Progress circle - centered in the 24x24 container */}
          {!isComplete && (
            <circle
              cx={fixedSize / 2}
              cy={fixedSize / 2}
              r={radius}
              fill="none"
              stroke={primaryColor}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              style={{
                transition: `stroke-dashoffset ${transitionDuration}s ease-in-out`,
              }}
            />
          )}
        </svg>
      )}
      {/* Check mark when complete */}
      {isComplete && <CheckIcon />}
    </div>
  );
};
