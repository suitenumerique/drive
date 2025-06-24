"use client";

import React, { useState } from "react";
import { VideoPlayer } from "./VideoPlayer";
import { Button } from "@openfun/cunningham-react";

export const VideoPlayerExample: React.FC = () => {
  const [currentVideo, setCurrentVideo] = useState(0);

  // Example video sources (replace with your actual video URLs)
  const videos = [
    {
      src: "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
      poster: "https://sample-videos.com/img/SampleVideo_1280x720_1mb.jpg",
      title: "Sample Video 1",
    },
    {
      src: "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
      poster:
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg",
      title: "Big Buck Bunny",
    },
  ];

  const handlePlay = () => {
    console.log("Video started playing");
  };

  const handlePause = () => {
    console.log("Video paused");
  };

  const handleEnded = () => {
    console.log("Video ended");
  };

  const handleTimeUpdate = (currentTime: number) => {
    // You can use this to sync with external components or analytics
    console.log("Current time:", currentTime);
  };

  return (
    <div style={{ padding: "20px", maxWidth: "800px", margin: "0 auto" }}>
      <h1>Lecteur Vidéo Personnalisé</h1>

      <div style={{ marginBottom: "20px" }}>
        <h2>{videos[currentVideo].title}</h2>
        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          {videos.map((video, index) => (
            <Button
              key={index}
              color={currentVideo === index ? "primary" : "secondary"}
              onClick={() => setCurrentVideo(index)}
            >
              Vidéo {index + 1}
            </Button>
          ))}
        </div>
      </div>

      <VideoPlayer
        src={videos[currentVideo].src}
        poster={videos[currentVideo].poster}
        autoPlay={false}
        muted={false}
        loop={false}
        controls={true}
        width="100%"
        height="auto"
        onPlay={handlePlay}
        onPause={handlePause}
        onEnded={handleEnded}
        onTimeUpdate={handleTimeUpdate}
      />

      <div
        style={{
          marginTop: "20px",
          padding: "16px",
          backgroundColor: "#f5f5f5",
          borderRadius: "8px",
        }}
      >
        <h3>Fonctionnalités du lecteur :</h3>
        <ul>
          <li>🎮 Contrôles personnalisés avec design moderne</li>
          <li>⏯️ Lecture/Pause avec icônes Material Design</li>
          <li>🔊 Contrôle du volume avec barre de progression</li>
          <li>🔇 Bouton mute/unmute</li>
          <li>⏱️ Affichage du temps de lecture</li>
          <li>📊 Barre de progression pour naviguer dans la vidéo</li>
          <li>🖥️ Mode plein écran</li>
          <li>📱 Design responsive pour mobile</li>
          <li>🌙 Support du thème sombre</li>
          <li>⏰ Auto-hide des contrôles après 3 secondes</li>
        </ul>
      </div>

      <div
        style={{
          marginTop: "20px",
          padding: "16px",
          backgroundColor: "#e8f4fd",
          borderRadius: "8px",
        }}
      >
        <h3>Utilisation :</h3>
        <pre
          style={{
            backgroundColor: "#f8f9fa",
            padding: "12px",
            borderRadius: "4px",
            overflow: "auto",
          }}
        >
          {`import { VideoPlayer } from './components/VideoPlayer';

<VideoPlayer
  src="https://example.com/video.mp4"
  poster="https://example.com/poster.jpg"
  autoPlay={false}
  muted={false}
  loop={false}
  controls={true}
  width="100%"
  height="auto"
  onPlay={() => console.log('Video started')}
  onPause={() => console.log('Video paused')}
  onEnded={() => console.log('Video ended')}
  onTimeUpdate={(time) => console.log('Current time:', time)}
/>`}
        </pre>
      </div>
    </div>
  );
};
