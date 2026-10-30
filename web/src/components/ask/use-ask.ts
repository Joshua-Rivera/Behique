"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { postSse } from "@/lib/api/sse";
import type { Citation, Usage } from "@/lib/api/types";

export type Step = { kind: string; label: string };

export type Turn = {
  id: number;
  question: string;
  allowWeb: boolean;
  steps: Step[];
  answer: string;
  citations: Citation[];
  usage: Usage | null;
  status: "running" | "done" | "stopped" | "error";
  error?: string;
  refused?: boolean;
  capped?: boolean;
  webEnabled?: boolean;
};

/** Conversation state for the Ask page. Kept in memory only, for privacy. */
export function useAsk() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const abort = useRef<AbortController | null>(null);
  const nextId = useRef(1);

  const update = (id: number, f: (t: Turn) => Partial<Turn>) =>
    setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, ...f(t) } : t)));

  const ask = useCallback(async (question: string, allowWeb: boolean) => {
    abort.current?.abort();
    const ctl = new AbortController();
    abort.current = ctl;
    const id = nextId.current++;
    setTurns((ts) => [
      ...ts,
      { id, question, allowWeb, steps: [], answer: "", citations: [], usage: null, status: "running" },
    ]);
    try {
      for await (const { event, data } of postSse(
        "/api/ask/stream",
        { question, allow_web: allowWeb },
        ctl.signal,
      )) {
        const d = data as Record<string, unknown>;
        if (event === "step") update(id, (t) => ({ steps: [...t.steps, d as Step] }));
        else if (event === "delta") update(id, (t) => ({ answer: t.answer + String(d.text ?? "") }));
        else if (event === "citations") update(id, () => ({ citations: d.citations as Citation[] }));
        else if (event === "usage") update(id, () => ({ usage: d as Usage }));
        else if (event === "done")
          update(id, () => ({
            status: "done",
            refused: Boolean(d.refused),
            capped: Boolean(d.step_cap_reached),
            webEnabled: Boolean(d.web_enabled),
          }));
        else if (event === "error")
          update(id, () => ({ status: "error", error: String(d.detail ?? "Something went wrong") }));
      }
      update(id, (t) => (t.status === "running" ? { status: "done" } : {}));
    } catch (err) {
      if (ctl.signal.aborted) update(id, () => ({ status: "stopped" }));
      else
        update(id, () => ({
          status: "error",
          error: err instanceof ApiError ? err.message : "Could not reach the server.",
        }));
    } finally {
      if (abort.current === ctl) abort.current = null;
    }
  }, []);

  const stop = useCallback(() => abort.current?.abort(), []);
  const clear = useCallback(() => {
    abort.current?.abort();
    setTurns([]);
  }, []);

  return { turns, ask, stop, clear, running: turns.some((t) => t.status === "running") };
}
