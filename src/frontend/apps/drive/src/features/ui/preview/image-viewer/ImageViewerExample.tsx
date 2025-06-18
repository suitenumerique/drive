"use client";

import React, { useState } from "react";
import { ImageViewer } from "./ImageViewer";

export const ImageViewerExample: React.FC = () => {
  const [selectedImage, setSelectedImage] = useState<string>("");

  // Example images (you can replace with your own images)
  const exampleImages = [
    "https://picsum.photos/800/600?random=1",
    "https://picsum.photos/1200/800?random=2",
    "https://picsum.photos/600/900?random=3",
    "https://picsum.photos/1000/1000?random=4",
  ];

  return (
    <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "20px", color: "#333" }}>
        Exemple d&apos;utilisation du ImageViewer
      </h1>

      <div style={{ marginBottom: "20px" }}>
        <h3 style={{ marginBottom: "10px", color: "#666" }}>
          Sélectionnez une image à visualiser :
        </h3>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {exampleImages.map((image, index) => (
            <button
              key={index}
              onClick={() => setSelectedImage(image)}
              style={{
                padding: "8px 16px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                background: selectedImage === image ? "#007bff" : "#fff",
                color: selectedImage === image ? "#fff" : "#333",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              Image {index + 1}
            </button>
          ))}
        </div>
      </div>

      {selectedImage && (
        <div
          style={{
            height: "600px",
            border: "1px solid #ddd",
            borderRadius: "8px",
          }}
        >
          <ImageViewer
            src={selectedImage}
            alt="Image d'exemple"
            initialZoom={1}
            minZoom={0.1}
            maxZoom={5}
            zoomStep={0.25}
          />
        </div>
      )}

      {!selectedImage && (
        <div
          style={{
            height: "400px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "2px dashed #ddd",
            borderRadius: "8px",
            color: "#666",
          }}
        >
          Sélectionnez une image ci-dessus pour commencer
        </div>
      )}

      <div
        style={{
          marginTop: "20px",
          padding: "16px",
          backgroundColor: "#f8f9fa",
          borderRadius: "8px",
        }}
      >
        <h3 style={{ marginBottom: "10px", color: "#333" }}>
          Fonctionnalités :
        </h3>
        <ul style={{ margin: 0, paddingLeft: "20px", color: "#666" }}>
          <li>
            Zoom avant/arrière avec la molette de la souris ou les boutons
          </li>
          <li>
            Déplacement de l&apos;image en cliquant et glissant (quand zoomé)
          </li>
          <li>
            Raccourcis clavier : + (zoom avant), - (zoom arrière), 0
            (réinitialiser)
          </li>
          <li>Interface responsive et accessible</li>
          <li>Support du mode sombre et des préférences de mouvement réduit</li>
        </ul>
      </div>
    </div>
  );
};
