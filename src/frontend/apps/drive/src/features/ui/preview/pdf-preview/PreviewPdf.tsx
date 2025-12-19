import { useMemo, useState, useEffect } from "react";
import { Document, Page } from "react-pdf";
import { pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ZoomControl } from "../image-viewer/ImageViewer";
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type PreviewPdfProps = {
  src: string;
};

export default function PreviewPdf({ src }: PreviewPdfProps) {
  const [numPages, setNumPages] = useState<number>();
  const options = useMemo(
    () => ({
      withCredentials: true,
      enableScripting: false,
      disableForms: true,
      disableAutoFetch: true,
      // disableFontFace: true,
    }),
    []
  );
  const [scale, setScale] = useState<number>(1);
  const [pageWidth, setPageWidth] = useState<number>(800);

  useEffect(() => {
    // Calculate page width based on container
    const updatePageWidth = () => {
      const maxWidth = 800;
      const containerPadding = 80;
      const availableWidth =
        typeof window !== "undefined"
          ? Math.min(maxWidth, window.innerWidth - containerPadding)
          : maxWidth;
      setPageWidth(availableWidth);
    };

    updatePageWidth();
    window.addEventListener("resize", updatePageWidth);
    return () => window.removeEventListener("resize", updatePageWidth);
  }, []);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
    setNumPages(numPages);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        overflow: "hidden",
        backgroundColor: "#1a1a1a",
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          overflowX: "hidden",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "20px",
          gap: "20px",
          backgroundColor: "#1a1a1a",
        }}
      >
        <Document
          options={options}
          file={src}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div
              style={{
                padding: "20px",
                textAlign: "center",
                color: "#ffffff",
              }}
            >
              Chargement du PDF...
            </div>
          }
        >
          {numPages &&
            Array.from(new Array(numPages), (el, index) => (
              <div
                key={`page_${index + 1}`}
                style={{
                  display: "flex",
                  justifyContent: "center",
                  marginBottom: "20px",
                }}
              >
                <Page
                  scale={scale}
                  width={pageWidth}
                  pageNumber={index + 1}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
              </div>
            ))}
        </Document>
      </div>
      <div className="image-viewer__controls">
        <ZoomControl
          zoomOut={() => setScale(scale - 0.1)}
          zoomIn={() => setScale(scale + 0.1)}
          zoom={scale}
          resetView={() => setScale(1)}
        />
      </div>
    </div>
  );
}
