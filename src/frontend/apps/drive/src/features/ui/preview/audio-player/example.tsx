"use client";

import React, { useState } from "react";
import { AudioPlayer } from "./index";

export const AudioPlayerExample: React.FC = () => {
  const [currentTrack, setCurrentTrack] = useState(0);

  // Example audio tracks
  const tracks = [
    {
      src: "/audio/test.m4a",
      title: "Sample Track 1",
      artist: "Artist Name",
    },
    {
      src: "/audio/test.m4a",
      title: "Sample Track 2",
      artist: "Another Artist",
    },
    {
      src: "/audio/test.m4a",
      title: "Sample Track 3",
      artist: "Third Artist",
    },
  ];

  const handleTrackEnded = () => {
    // Auto-play next track
    setCurrentTrack((prev) => (prev + 1) % tracks.length);
  };

  const handleTimeUpdate = (currentTime: number) => {
    // You can use this to sync with other components or save progress
    console.log("Current time:", currentTime);
  };

  return (
    <div style={{ padding: "20px", maxWidth: "600px", margin: "0 auto" }}>
      <h2>Lecteur Audio Personnalisé</h2>

      <div style={{ marginBottom: "20px" }}>
        <p>
          Piste actuelle: {currentTrack + 1} / {tracks.length}
        </p>
        <button
          onClick={() =>
            setCurrentTrack(
              (prev) => (prev - 1 + tracks.length) % tracks.length
            )
          }
          disabled={currentTrack === 0}
          style={{ marginRight: "10px" }}
        >
          Précédent
        </button>
        <button
          onClick={() => setCurrentTrack((prev) => (prev + 1) % tracks.length)}
        >
          Suivant
        </button>
      </div>

      <AudioPlayer
        src={tracks[currentTrack].src}
        title={tracks[currentTrack].title}
        artist={tracks[currentTrack].artist}
        onEnded={handleTrackEnded}
        onTimeUpdate={handleTimeUpdate}
        onPlay={() => console.log("Track started playing")}
        onPause={() => console.log("Track paused")}
      />

      <div style={{ marginTop: "20px", fontSize: "14px", color: "#666" }}>
        <h3>Fonctionnalités incluses :</h3>
        <ul>
          <li>Lecture/Pause avec bouton central</li>
          <li>Barre de progression interactive</li>
          <li>Contrôle du volume avec bouton mute</li>
          <li>Affichage du temps écoulé/total</li>
          <li>Design responsive</li>
          <li>Support du mode sombre</li>
          <li>Accessibilité (focus, aria-labels)</li>
          <li>Callbacks pour synchronisation</li>
        </ul>
      </div>
    </div>
  );
};
