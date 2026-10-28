"use client";

import { useCallback, useEffect, useState } from "react";

import { read, write } from "./storage";

export type PaneLimits = { min: number; max: number; initial: number };

export const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

/** A pixel size for one pane, restored from and saved to localStorage under `key`. */
export function usePaneSize(key: string, limits: PaneLimits) {
  const { min, max, initial } = limits;
  const [size, setSizeState] = useState(initial);

  useEffect(() => {
    const saved = Number(read(`behique.pane.${key}`));
    if (Number.isFinite(saved) && saved > 0) setSizeState(clamp(saved, min, max));
    // Restore once on mount; later limit changes clamp through setSize.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const setSize = useCallback(
    (next: number) => {
      const v = Math.round(clamp(next, min, max));
      setSizeState(v);
      write(`behique.pane.${key}`, String(v));
    },
    [key, min, max],
  );

  const reset = useCallback(() => {
    setSizeState(initial);
    write(`behique.pane.${key}`, null);
  }, [key, initial]);

  return { size: clamp(size, min, max), setSize, reset };
}
