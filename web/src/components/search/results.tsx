"use client";

import { FileText } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import type { Hit } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { highlight } from "@/lib/highlight";

const RETRIEVER_LABEL: Record<string, string> = { vector: "vector", bm25: "keyword" };

export function groupByFile(hits: Hit[]): { path: string; fileId: number; hits: Hit[] }[] {
  const groups = new Map<number, { path: string; fileId: number; hits: Hit[] }>();
  for (const h of hits) {
    const g = groups.get(h.file_id) ?? { path: h.path, fileId: h.file_id, hits: [] };
    g.hits.push(h);
    groups.set(h.file_id, g);
  }
  return [...groups.values()];
}

function snippet(text: string, max = 260) {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > max ? flat.slice(0, max) + " …" : flat;
}

export function Results({
  hits,
  terms,
  selected,
  onSelect,
  onOpen,
}: {
  hits: Hit[];
  terms: string[];
  selected: number | null;
  onSelect: (chunkId: number) => void;
  onOpen: (chunkId: number) => void;
}) {
  const groups = useMemo(() => groupByFile(hits), [hits]);
  const top = hits[0]?.score || 1;
  const refs = useRef(new Map<number, HTMLDivElement>());

  useEffect(() => {
    if (selected !== null) refs.current.get(selected)?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  return (
    <div role="listbox" aria-label="Search results" className="pb-6">
      {groups.map((g) => (
        <div key={g.fileId} role="group" aria-label={g.path} className="border-b-[0.5px] border-line">
          <div aria-hidden className="flex items-center gap-1.5 px-4 pb-1 pt-3 font-mono text-xs text-stone">
            <FileText className="size-3.5" aria-hidden />
            <span className="truncate">{g.path}</span>
          </div>
            {g.hits.map((h) => {
              const active = h.chunk_id === selected;
              return (
                <div
                  key={h.chunk_id}
                  ref={(el) => {
                    if (el) refs.current.set(h.chunk_id, el);
                    else refs.current.delete(h.chunk_id);
                  }}
                  role="option"
                  id={`hit-${h.chunk_id}`}
                  aria-selected={active}
                  onClick={() => onSelect(h.chunk_id)}
                  onDoubleClick={() => onOpen(h.chunk_id)}
                  className={cn(
                    "cursor-pointer border-l-2 px-4 py-2 transition-colors duration-150 ease-out",
                    active ? "border-ochre bg-ochre-soft" : "border-transparent hover:bg-sand",
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="min-w-0 flex-1 truncate text-sm text-clay">
                      {h.heading_path || h.symbol || "—"}
                    </span>
                    <span className="flex gap-1.5 text-[11px] text-moss">
                      {h.retrievers.map((r) => (
                        <span key={r}>{RETRIEVER_LABEL[r] ?? r}</span>
                      ))}
                    </span>
                    <span
                      className="h-1 w-12 shrink-0 bg-line"
                      role="meter"
                      aria-label="Relevance"
                      aria-valuemin={0}
                      aria-valuemax={1}
                      aria-valuenow={Number((h.score / top).toFixed(2))}
                    >
                      <span
                        className="block h-full bg-moss"
                        style={{ width: `${Math.max(6, (h.score / top) * 100)}%` }}
                      />
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-3 text-sm leading-snug text-ink">
                    {highlight(snippet(h.text), terms)}
                  </p>
                </div>
              );
            })}
        </div>
      ))}
    </div>
  );
}
