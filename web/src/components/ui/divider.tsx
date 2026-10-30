"use client";

import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { cn } from "@/lib/cn";

const STEP = 16;

/**
 * Vertical pane divider: a 0.5px hairline that becomes a 2px clay line on hover, focus
 * or drag. Focusable `role="separator"`; ←/→ resize, double-click resets.
 */
export function Divider({
  label,
  size,
  min,
  max,
  onResize,
  onReset,
}: {
  label: string;
  size: number;
  min: number;
  max: number;
  onResize: (size: number) => void;
  onReset: () => void;
}) {
  const start = useRef<{ x: number; size: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  function onPointerDown(e: PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    start.current = { x: e.clientX, size };
    setDragging(true);
  }

  function onPointerMove(e: PointerEvent<HTMLDivElement>) {
    if (!start.current) return;
    onResize(start.current.size + e.clientX - start.current.x);
  }

  function onPointerUp(e: PointerEvent<HTMLDivElement>) {
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
    start.current = null;
    setDragging(false);
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const delta = { ArrowLeft: -STEP, ArrowRight: STEP }[e.key];
    if (delta) {
      e.preventDefault();
      onResize(size + delta);
    } else if (e.key === "Home") {
      e.preventDefault();
      onResize(min);
    } else if (e.key === "End") {
      e.preventDefault();
      onResize(max);
    } else if (e.key === "Enter") {
      e.preventDefault();
      onReset();
    }
  }

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={size}
      aria-valuemin={min}
      aria-valuemax={max}
      tabIndex={0}
      data-dragging={dragging || undefined}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={onReset}
      onKeyDown={onKeyDown}
      className={cn(
        "group relative z-10 -mx-1 w-2 shrink-0 cursor-col-resize touch-none select-none",
        "focus-visible:outline-none",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute inset-y-0 left-1/2 w-[0.5px] -translate-x-1/2 bg-line transition-all duration-150 ease-out",
          "group-hover:w-0.5 group-hover:bg-clay group-focus-visible:w-0.5 group-focus-visible:bg-clay",
          dragging && "w-0.5 bg-clay",
        )}
      />
    </div>
  );
}
