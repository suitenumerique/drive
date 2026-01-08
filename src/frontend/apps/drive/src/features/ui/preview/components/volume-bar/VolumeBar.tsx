import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useEffect } from "react";

export type VolumeBarProps = {
  volume: number;
  isMuted: boolean;
  toggleMute: () => void;
  handleVolumeChange: (newVolume: number) => void;
};

export const VolumeBar = ({
  volume,
  isMuted,
  toggleMute,
  handleVolumeChange,
}: VolumeBarProps) => {
  const volumePercentage = isMuted ? 0 : volume * 100;
  const volumeIsMuted = volume === 0 || isMuted;
  const getVolumeIcon = () => {
    if (isMuted || volume === 0) return "volume_off";
    if (volume < 0.5) return "volume_down";
    return "volume_up";
  };

  const onVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleVolumeChange(parseFloat(e.target.value));
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.code) {
        case "ArrowUp":
          event.preventDefault();
          handleVolumeChange(Math.min(1, volume + 0.1));

          break;
        case "ArrowDown":
          event.preventDefault();
          handleVolumeChange(Math.max(0, volume - 0.1));
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleVolumeChange, volume]);

  return (
    <div className="suite-volume-bar">
      <Button
        variant="tertiary"
        onClick={toggleMute}
        className="suite-volume-bar__btn-mute"
        icon={<Icon name={getVolumeIcon()} />}
      />
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={volumeIsMuted ? 0 : volume}
        onChange={onVolumeChange}
        className="suite-volume-bar__bar"
        style={
          {
            "--volume-percentage": `${volumePercentage}%`,
          } as React.CSSProperties
        }
      />
    </div>
  );
};
