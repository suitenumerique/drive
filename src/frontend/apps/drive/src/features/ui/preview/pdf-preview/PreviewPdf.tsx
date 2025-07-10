interface PreviewPdfProps {
  src?: string;
}

export const PreviewPdf = ({ src }: PreviewPdfProps) => {
  return (
    <iframe
      src={src}
      width="100%"
      height="100%"
      className="pdf-container__iframe"
    />
  );
};
