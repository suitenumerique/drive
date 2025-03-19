type ExplorerDragOverlayProps = {
  count: number;
};

export const ExplorerDragOverlay = ({ count }: ExplorerDragOverlayProps) => {
  const filesCount = count > 0 ? count : 1;
  return (
    <div className="explorer__drag-overlay">
      {filesCount} fichiers sélectionnés
    </div>
  );
};
