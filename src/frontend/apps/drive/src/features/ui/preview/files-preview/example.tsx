import React, { useState } from "react";
import { FilePreview } from "./index";

export const FilePreviewExample: React.FC = () => {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // Example files of different types
  const exampleFiles = [
    {
      title: "Document.pdf",
      mimetype: "application/pdf",
      url: "http://localhost:3000/pdf/test.pdf",
    },
    {
      title: "Image.jpg",
      mimetype: "image/jpeg",
      url: "https://picsum.photos/800/600",
    },
    {
      title: "Video.mp4",
      mimetype: "video/mp4",
      url: "https://djdxvpsdluyhwbuqhfre.supabase.co/storage/v1/object/public/test//test.mov",
    },
    {
      title: "Audio.mp3",
      mimetype: "audio/mpeg",
      url: "http://localhost:3000/audio/test.m4a",
    },
    {
      title: "Document.txt",
      mimetype: "text/plain",
      url: "https://example.com/document.txt",
    },
  ];

  const handleOpenPreview = () => {
    setIsPreviewOpen(true);
  };

  const handleClosePreview = () => {
    setIsPreviewOpen(false);
  };

  return (
    <div>
      <button
        onClick={handleOpenPreview}
        style={{
          padding: "12px 24px",
          backgroundColor: "#3b82f6",
          color: "white",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "16px",
        }}
      >
        Ouvrir la prévisualisation
      </button>

      <FilePreview
        isOpen={isPreviewOpen}
        onClose={handleClosePreview}
        title="Prévisualisation de fichiers"
        files={exampleFiles}
        initialIndexFile={0}
      />
    </div>
  );
};
