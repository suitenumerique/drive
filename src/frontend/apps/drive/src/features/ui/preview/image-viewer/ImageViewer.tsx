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

interface TouchPoint {
  x: number;
  y: number;
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

  // Touch state for mobile
  const [touchStart, setTouchStart] = useState<TouchPoint | null>(null);
  const [touchDistance, setTouchDistance] = useState<number | null>(null);
  const [initialZoomOnTouch, setInitialZoomOnTouch] = useState<number>(1);

  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Calculate distance between two touch points
  const getTouchDistance = useCallback(
    (touch1: React.Touch, touch2: React.Touch): number => {
      const dx = touch1.clientX - touch2.clientX;
      const dy = touch1.clientY - touch2.clientY;
      return Math.sqrt(dx * dx + dy * dy);
    },
    []
  );

  // Preload image to get dimensions before displaying
  useEffect(() => {
    const preloadImage = new Image();

    preloadImage.onload = () => {
      if (containerRef.current) {
        const { naturalWidth, naturalHeight } = preloadImage;
        const containerRect = containerRef.current.getBoundingClientRect();

        let calculatedZoom = 1;
        let displayWidth = naturalWidth;
        let displayHeight = naturalHeight;

        // Add margin factor (20% of container size)
        const marginFactor = 0.2;
        const availableWidth = containerRect.width * (1 - marginFactor);
        const availableHeight = containerRect.height * (1 - marginFactor);

        if (
          naturalWidth <= availableWidth &&
          naturalHeight <= availableHeight
        ) {
          // Original size fits with margin, zoom = 1 corresponds to original size
          calculatedZoom = 1;
          displayWidth = naturalWidth;
          displayHeight = naturalHeight;
        } else {
          // Original size doesn't fit with margin, calculate zoom to fit
          const availableAspectRatio = availableWidth / availableHeight;
          const imageAspectRatio = naturalWidth / naturalHeight;

          if (imageAspectRatio > availableAspectRatio) {
            // Image is wider than available space
            calculatedZoom = availableWidth / naturalWidth;
            displayWidth = availableWidth;
            displayHeight = availableWidth / imageAspectRatio;
          } else {
            // Image is taller than available space
            calculatedZoom = availableHeight / naturalHeight;
            displayHeight = availableHeight;
            displayWidth = availableHeight * imageAspectRatio;
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
    };

    preloadImage.onerror = () => {
      // Handle error if image fails to load
      setImageLoaded(true); // Still set to true to hide loading spinner
    };

    preloadImage.src = src;
  }, [src]);

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

  // Handle touch start for mobile
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();

      if (e.touches.length === 1) {
        // Single touch - start dragging
        if (isImageExceedingBounds()) {
          setIsDragging(true);
          setTouchStart({
            x: e.touches[0].clientX - position.x,
            y: e.touches[0].clientY - position.y,
          });
        }
      } else if (e.touches.length === 2) {
        // Two touches - start pinch zoom
        setIsDragging(false);
        const distance = getTouchDistance(e.touches[0], e.touches[1]);
        setTouchDistance(distance);
        setInitialZoomOnTouch(zoom);
      }
    },
    [isImageExceedingBounds, position, zoom, getTouchDistance]
  );

  // Handle touch move for mobile
  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();

      if (e.touches.length === 1 && isDragging && touchStart) {
        // Single touch - continue dragging
        const newPosition = {
          x: e.touches[0].clientX - touchStart.x,
          y: e.touches[0].clientY - touchStart.y,
        };

        const constrainedPosition = getConstrainedPosition(newPosition);
        setPosition(constrainedPosition);
      } else if (e.touches.length === 2 && touchDistance !== null) {
        // Two touches - handle pinch zoom
        const currentDistance = getTouchDistance(e.touches[0], e.touches[1]);
        const scale = currentDistance / touchDistance;
        const newZoom = Math.max(
          minZoom,
          Math.min(maxZoom, initialZoomOnTouch * scale)
        );
        setZoom(newZoom);
      }
    },
    [
      isDragging,
      touchStart,
      touchDistance,
      initialZoomOnTouch,
      getConstrainedPosition,
      getTouchDistance,
      minZoom,
      maxZoom,
    ]
  );

  // Handle touch end for mobile
  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
    setTouchStart(null);
    setTouchDistance(null);
  }, []);

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
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{
          cursor: getCursorStyle(),
          touchAction: "none", // Prevent default touch behaviors
        }}
      >
        {imageLoaded && (
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
              draggable={false}
              style={{
                width: imageDimensions.naturalWidth,
                height: imageDimensions.naturalHeight,
              }}
            />
          </div>
        )}

        {!imageLoaded && (
          <div className="image-viewer__loading">
            <div className="image-viewer__spinner"></div>
            <span>Chargement de l&apos;image...</span>
          </div>
        )}
      </div>

      <div className="image-viewer__controls">
        <ZoomControl
          zoomOut={zoomOut}
          zoomIn={zoomIn}
          zoom={zoom}
          resetView={resetView}
        />
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
      <Button variant="tertiary" color="neutral" onClick={zoomOut}>
        <Icon name="zoom_out" />
      </Button>
      <div className="zoom-control__value" role="button" onClick={resetView}>
        {Math.round(zoom * 100)}%
      </div>
      <Button variant="tertiary" color="neutral" onClick={zoomIn}>
        <Icon name="zoom_in" />
      </Button>
    </div>
  );
};
