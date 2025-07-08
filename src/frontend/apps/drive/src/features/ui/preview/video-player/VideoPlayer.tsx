"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import clsx from "clsx";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { ProgressBar } from "../components/duration-bar/DurationBar";
import { PreviewControls } from "../components/controls/PreviewControls";

interface VideoPlayerProps {
  src: string;
  poster?: string;
  className?: string;
  autoPlay?: boolean;
  muted?: boolean;
  loop?: boolean;
  controls?: boolean;
  width?: string | number;
  height?: string | number;
  onPlay?: () => void;
  onPause?: () => void;
  onEnded?: () => void;
  onTimeUpdate?: (currentTime: number) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  poster,
  className,
  autoPlay = false,
  muted = false,
  loop = false,
  controls = true,
  width = "100%",
  height = "auto",
  onPlay,
  onPause,
  onEnded,
  onTimeUpdate,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(muted);
  const [showControls, setShowControls] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showStatusIcon, setShowStatusIcon] = useState(false);
  const [statusIcon, setStatusIcon] = useState<"play" | "pause">("play");

  // Handle play/pause
  const togglePlay = useCallback(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
    }
  }, [isPlaying]);

  // Handle volume change
  const handleVolumeChange = useCallback((newVolume: number) => {
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
      setIsMuted(newVolume === 0);
    }
  }, []);

  // Handle mute toggle
  const toggleMute = useCallback(() => {
    if (videoRef.current) {
      const newIsMuted = !isMuted;
      videoRef.current.muted = newIsMuted;
      setIsMuted(newIsMuted);
    }
  }, [isMuted]);

  // Handle seek
  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
  }, []);

  // Handle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (videoRef.current) {
      if (!isFullscreen) {
        // Enable native controls for fullscreen
        videoRef.current.controls = true;
        if (videoRef.current.requestFullscreen) {
          videoRef.current.requestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        }
      }
    }
  }, [isFullscreen]);

  // Handle rewind 10 seconds
  const rewind10Seconds = useCallback(() => {
    if (videoRef.current) {
      const newTime = Math.max(0, currentTime - 10);
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  }, [currentTime]);

  // Handle forward 10 seconds
  const forward10Seconds = useCallback(() => {
    if (videoRef.current) {
      const newTime = Math.min(duration, currentTime + 10);
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  }, [currentTime, duration]);

  // Event handlers
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
      // Disable native controls when not in fullscreen
      videoRef.current.controls = false;
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      onTimeUpdate?.(videoRef.current.currentTime);
    }
  };

  const handlePlay = () => {
    setIsPlaying(true);
    setStatusIcon("play");
    setShowStatusIcon(true);
    setTimeout(() => setShowStatusIcon(false), 2000);
    onPlay?.();
  };

  const handlePause = () => {
    setIsPlaying(false);
    setStatusIcon("pause");
    setShowStatusIcon(true);
    setTimeout(() => setShowStatusIcon(false), 2000);
    onPause?.();
  };

  const handleEnded = () => {
    setIsPlaying(false);
    onEnded?.();
  };

  const handleVolumeInput = () => {
    if (videoRef.current) {
      setVolume(videoRef.current.volume);
    }
  };

  // Fullscreen change handler
  useEffect(() => {
    const handleFullscreenChange = () => {
      const fullscreenElement = !!document.fullscreenElement;
      setIsFullscreen(fullscreenElement);

      if (videoRef.current) {
        if (fullscreenElement) {
          // Enable native controls in fullscreen
          videoRef.current.controls = true;
        } else {
          // Disable native controls when exiting fullscreen
          videoRef.current.controls = false;
        }
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  // Auto-hide controls (only when not in fullscreen)
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (isPlaying && showControls && !isFullscreen) {
      timeout = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
    return () => clearTimeout(timeout);
  }, [isPlaying, showControls, isFullscreen]);

  // Get volume icon name

  return (
    <div
      className={clsx("video-player", className)}
      style={{ width, height }}
      onMouseEnter={() => !isFullscreen && setShowControls(true)}
      onMouseLeave={() => isPlaying && !isFullscreen && setShowControls(false)}
    >
      <div className="video-player__video__wrapper">
        <video
          ref={videoRef}
          src={src}
          poster={poster}
          autoPlay={autoPlay}
          muted={muted}
          loop={loop}
          controls={false} // We'll manage this dynamically
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
          onPlay={handlePlay}
          onPause={handlePause}
          onEnded={handleEnded}
          onVolumeChange={handleVolumeInput}
          onClick={togglePlay}
          className="video-player__video"
        />
        {/* Status icon overlay */}
        {showStatusIcon && (
          <div className="video-player__status-icon">
            <Icon
              color="#5E5E5E"
              name={statusIcon === "play" ? "play_arrow" : "pause"}
            />
          </div>
        )}
      </div>

      {controls && !isFullscreen && (
        <div className={clsx("video-player__controls", {})}>
          {/* Progress bar */}

          <ProgressBar
            duration={duration}
            currentTime={currentTime}
            handleSeek={handleSeek}
          />

          {/* Control buttons */}
          <PreviewControls
            togglePlay={togglePlay}
            isPlaying={isPlaying}
            rewind10Seconds={rewind10Seconds}
            forward10Seconds={forward10Seconds}
            volume={volume}
            isMuted={isMuted}
            toggleMute={toggleMute}
            handleVolumeChange={handleVolumeChange}
            toggleFullscreen={toggleFullscreen}
            isFullscreen={isFullscreen}
            showFullscreenBtn={true}
          />
        </div>
      )}
    </div>
  );
};
