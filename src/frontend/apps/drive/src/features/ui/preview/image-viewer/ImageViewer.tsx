"use client";

import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import React, { useState, useRef, useCallback, useEffect } from "react";

interface ImageViewerProps {
  src: string;
  alt?: string;
  className?: string;
  initialZoom?: number;
  minZoom?: number;
  maxZoom?: number;
  zoomStep?: number;
}

interface ImageDimensions {
  width: number;
  height: number;
  naturalWidth: number;
  naturalHeight: number;
  originalZoom: number;
}

export const ImageViewer: React.FC<ImageViewerProps> = ({
  src,
  alt = "Image",
  className = "",
  initialZoom = 1,
  minZoom = 0.1,
  maxZoom = 5,
  zoomStep = 0.25,
}) => {
  const [zoom, setZoom] = useState(initialZoom);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState<ImageDimensions>({
    width: 0,
    height: 0,
    naturalWidth: 0,
    naturalHeight: 0,
    originalZoom: 1,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Calculate if image exceeds container bounds
  const isImageExceedingBounds = useCallback(() => {
    if (!containerRef.current || !imageRef.current) return false;

    const containerRect = containerRef.current.getBoundingClientRect();
    const scaledWidth = imageDimensions.naturalWidth * zoom;
    const scaledHeight = imageDimensions.naturalHeight * zoom;

    return (
      scaledWidth > containerRect.width || scaledHeight > containerRect.height
    );
  }, [zoom, imageDimensions]);

  // Calculate position constraints
  const getConstrainedPosition = useCallback(
    (newPosition: { x: number; y: number }) => {
      if (!containerRef.current || !imageRef.current) return newPosition;

      const containerRect = containerRef.current.getBoundingClientRect();
      const scaledWidth = imageDimensions.naturalWidth * zoom;
      const scaledHeight = imageDimensions.naturalHeight * zoom;

      // Calculate boundaries
      const maxX = Math.max(0, (scaledWidth - containerRect.width) / 2);
      const minX = -maxX;
      const maxY = Math.max(0, (scaledHeight - containerRect.height) / 2);
      const minY = -maxY;

      return {
        x: Math.max(minX, Math.min(maxX, newPosition.x)),
        y: Math.max(minY, Math.min(maxY, newPosition.y)),
      };
    },
    [zoom, imageDimensions]
  );

  // Handle image load to get natural dimensions and calculate initial zoom
  const handleImageLoad = useCallback(() => {
    if (imageRef.current && containerRef.current) {
      const { naturalWidth, naturalHeight } = imageRef.current;
      const containerRect = containerRef.current.getBoundingClientRect();

      // Calculate if original size fits in container
      const fitsHorizontally = naturalWidth <= containerRect.width;
      const fitsVertically = naturalHeight <= containerRect.height;

      let calculatedZoom = 1;
      let displayWidth = naturalWidth;
      let displayHeight = naturalHeight;

      if (fitsHorizontally && fitsVertically) {
        // Original size fits, zoom = 1 corresponds to original size
        calculatedZoom = 1;
        displayWidth = naturalWidth;
        displayHeight = naturalHeight;
      } else {
        // Original size doesn't fit, calculate zoom to fit
        const containerAspectRatio = containerRect.width / containerRect.height;
        const imageAspectRatio = naturalWidth / naturalHeight;

        if (imageAspectRatio > containerAspectRatio) {
          // Image is wider than container
          calculatedZoom = containerRect.width / naturalWidth;
          displayWidth = containerRect.width;
          displayHeight = containerRect.width / imageAspectRatio;
        } else {
          // Image is taller than container
          calculatedZoom = containerRect.height / naturalHeight;
          displayHeight = containerRect.height;
          displayWidth = containerRect.height * imageAspectRatio;
        }
      }

      setImageDimensions({
        width: displayWidth,
        height: displayHeight,
        naturalWidth,
        naturalHeight,
        originalZoom: calculatedZoom,
      });

      // Set initial zoom based on calculated zoom
      setZoom(calculatedZoom);
      setImageLoaded(true);
    }
  }, []);

  // Zoom in
  const zoomIn = useCallback(() => {
    setZoom((prevZoom) => {
      const newZoom = Math.min(prevZoom + zoomStep, maxZoom);
      return newZoom;
    });
  }, [zoomStep, maxZoom]);

  // Zoom out
  const zoomOut = useCallback(() => {
    setZoom((prevZoom) => {
      const newZoom = Math.max(prevZoom - zoomStep, minZoom);
      return newZoom;
    });
  }, [zoomStep, minZoom]);

  // Reset zoom and position
  const resetView = useCallback(() => {
    setZoom(imageDimensions.originalZoom);
    setPosition({ x: 0, y: 0 });
  }, [imageDimensions.originalZoom]);

  // Handle mouse down for dragging
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isImageExceedingBounds()) {
        setIsDragging(true);
        setDragStart({
          x: e.clientX - position.x,
          y: e.clientY - position.y,
        });
      }
    },
    [isImageExceedingBounds, position]
  );

  // Handle mouse move for dragging
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging && isImageExceedingBounds()) {
        const newPosition = {
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        };

        const constrainedPosition = getConstrainedPosition(newPosition);
        setPosition(constrainedPosition);
      }
    },
    [isDragging, dragStart, isImageExceedingBounds, getConstrainedPosition]
  );

  // Handle mouse up to stop dragging
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Handle wheel for zoom
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -zoomStep : zoomStep;
      setZoom((prevZoom) => {
        const newZoom = Math.max(minZoom, Math.min(maxZoom, prevZoom + delta));
        return newZoom;
      });
    },
    [zoomStep, minZoom, maxZoom]
  );

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target !== containerRef.current) return;

      switch (e.key) {
        case "+":
        case "=":
          e.preventDefault();
          zoomIn();
          break;
        case "-":
          e.preventDefault();
          zoomOut();
          break;
        case "0":
          e.preventDefault();
          resetView();
          break;
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener("keydown", handleKeyDown);
      return () => container.removeEventListener("keydown", handleKeyDown);
    }
  }, [zoomIn, zoomOut, resetView]);

  // Update position when zoom changes to keep image centered and constrained
  useEffect(() => {
    if (zoom <= imageDimensions.originalZoom) {
      setPosition({ x: 0, y: 0 });
    } else {
      // Constrain position when zoom changes
      const constrainedPosition = getConstrainedPosition(position);
      setPosition(constrainedPosition);
    }
  }, [zoom, getConstrainedPosition, imageDimensions.originalZoom]);

  // Determine cursor style
  const getCursorStyle = useCallback(() => {
    if (isDragging) return "grabbing";
    if (isImageExceedingBounds()) return "grab";
    return "default";
  }, [isDragging, isImageExceedingBounds]);

  return (
    <div className={`image-viewer ${className}`}>
      <div
        ref={containerRef}
        className="image-viewer__container"
        tabIndex={0}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        style={{
          cursor: getCursorStyle(),
        }}
      >
        <div
          className="image-viewer__image-wrapper"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
          }}
        >
          <img
            ref={imageRef}
            src={src}
            alt={alt}
            className="image-viewer__image"
            onLoad={handleImageLoad}
            draggable={false}
            style={{
              width: imageDimensions.naturalWidth,
              height: imageDimensions.naturalHeight,
            }}
          />
        </div>

        {!imageLoaded && (
          <div className="image-viewer__loading">
            <div className="image-viewer__spinner"></div>
            <span>Chargement de l&apos;image...</span>
          </div>
        )}
      </div>

      <div className="image-viewer__help">
        <div className="image-viewer__controls">
          <ZoomControl
            zoomOut={zoomOut}
            zoomIn={zoomIn}
            zoom={zoom}
            resetView={resetView}
          />
        </div>
      </div>
    </div>
  );
};

interface ZoomControlProps {
  zoomOut: () => void;
  zoomIn: () => void;
  zoom: number;
  resetView: () => void;
}

export const ZoomControl = ({
  zoomOut,
  zoomIn,
  zoom,
  resetView,
}: ZoomControlProps) => {
  return (
    <div className="zoom-control">
      <Button color="tertiary-text" onClick={zoomOut}>
        <Icon name="zoom_out" />
      </Button>
      <div className="zoom-control__value" role="button" onClick={resetView}>
        {Math.round(zoom * 100)}%
      </div>
      <Button color="tertiary-text" onClick={zoomIn}>
        <Icon name="zoom_in" />
      </Button>
    </div>
  );
};
