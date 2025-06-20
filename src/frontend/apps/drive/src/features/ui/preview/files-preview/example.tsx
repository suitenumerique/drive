import React, { useState } from "react";
import { FilePreview, FilePreviewType } from "./index";

type FilePreviewExampleProps = {
  files?: FilePreviewType[];
};

export const FilePreviewExample: React.FC<FilePreviewExampleProps> = ({
  files,
}) => {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // Example files of different types
  const exampleFiles: FilePreviewType[] = files ?? [
    {
      id: "1",
      title: "Document.pdf",
      mimetype: "application/pdf",
      url: "http://localhost:3000/pdf/test.pdf",
    },
    {
      id: "2",
      title: "Image.jpg",
      mimetype: "image/jpeg",
      url: "https://picsum.photos/800/600",
    },
    {
      id: "3",
      title: "Video.mp4",
      mimetype: "video/mp4",
      url: "http://localhost:8083/media/item/3ad5968d-3b2e-466b-a20a-068ea059bcdc/Enregistrement de l’écran 2025-06-20 à 08.59.43.mov",
    },
    {
      id: "4",
      title: "Audio.mp3",
      mimetype: "audio/mpeg",
      url: "http://localhost:3000/audio/test.m4a",
    },
    {
      id: "5",
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
