import { DragEvent, PropsWithChildren } from "react";

const stopPropagation = (event: DragEvent) => {
  event.stopPropagation();
};

/**
 * Stops drag events from bubbling up the React tree past this component.
 *
 * Content portaled from inside the explorer (modals, previews) still
 * bubbles its synthetic drag events to the explorer dropzone, which
 * shows the global upload toast. Wrap such content with this barrier
 * when it handles file drags itself.
 */
export const DragEventBarrier = ({ children }: PropsWithChildren) => {
  return (
    <div
      style={{ display: "contents" }}
      onDragEnter={stopPropagation}
      onDragOver={stopPropagation}
      onDragLeave={stopPropagation}
      onDrop={stopPropagation}
    >
      {children}
    </div>
  );
};
