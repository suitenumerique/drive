import dynamic from "next/dynamic";

const PDFViewer = dynamic(
  () => import("@/features/ui/preview/pdf-preview/PreviewPdf"),
  {
    ssr: false,
  }
);

export default function Test() {
  return <PDFViewer src="http://localhost:3000/pdf.pdf" />;
}
