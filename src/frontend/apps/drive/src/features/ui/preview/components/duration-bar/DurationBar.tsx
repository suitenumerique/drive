const formatTime = (time: number): string => {
  const minutes = Math.floor(time / 60);
  const seconds = Math.floor(time % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

type DurationBarProps = {
  duration: number;
  currentTime: number;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
};

export const ProgressBar = ({
  duration,
  currentTime,
  handleSeek,
}: DurationBarProps) => {
  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="suite-progress-bar">
      <div className="suite-progress-bar__time">{formatTime(currentTime)}</div>
      <input
        type="range"
        min={0}
        max={duration || 0}
        value={currentTime}
        step={0.01}
        onChange={handleSeek}
        className="suite-progress-bar__bar"
        style={
          {
            "--progress-percentage": `${progressPercentage}%`,
          } as React.CSSProperties
        }
      />
      <div className="suite-progress-bar__time">{formatTime(duration)}</div>
    </div>
  );
};
