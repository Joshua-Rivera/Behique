"use client";

import { Check, Copy } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useFileWindow, useFullFile } from "@/lib/api/hooks";
import { citation, highlight, lineRange } from "@/lib/highlight";

export type PreviewTarget = {
  fileId: number;
  chunkId: number;
  path?: string;
  /** The chunk's own text and offsets, when known (from a search hit). */
  text?: string;
  startChar?: number;
  endChar?: number;
};

/** A chunk shown in its surroundings, with the chunk itself highlighted. */
export function Preview({ target, terms = [] }: { target: PreviewTarget; terms?: string[] }) {
  const win = useFileWindow(target.fileId, target.chunkId, 2);
  const full = useFullFile(target.fileId);
  const [copied, setCopied] = useState(false);
  const markRef = useRef<HTMLElement>(null);

  const parts = useMemo(() => {
    const text = win.data?.text ?? "";
    if (!text) return null;
    let start = target.text ? text.indexOf(target.text) : -1;
    let end = start >= 0 ? start + target.text!.length : -1;
    if (start < 0 && target.startChar !== undefined && win.data?.start_char !== undefined) {
      start = Math.max(0, target.startChar - win.data.start_char);
      end = Math.min(text.length, (target.endChar ?? target.startChar) - win.data.start_char);
    }
    if (start < 0) return { before: text, match: "", after: "" };
    return { before: text.slice(0, start), match: text.slice(start, end), after: text.slice(end) };
  }, [win.data, target]);

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: "center" });
  }, [parts]);

  useEffect(() => setCopied(false), [target.chunkId]);

  const path = win.data?.path ?? target.path ?? "";
  const lines = useMemo(() => {
    const fullText = full.data?.text;
    if (!fullText) return null;
    const chunkText = target.text ?? parts?.match ?? "";
    let start = chunkText ? fullText.indexOf(chunkText) : -1;
    if (start < 0 && target.startChar !== undefined) start = target.startChar;
    if (start < 0) return null;
    return lineRange(fullText, start, start + (chunkText.length || 1));
  }, [full.data, target, parts]);

  async function copy() {
    const text = lines ? citation(path, lines) : path;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  const heading = win.data?.heading_path || win.data?.symbol;

  return (
    <article aria-label="Preview" className="flex h-full min-h-0 flex-col">
      <header className="flex items-start justify-between gap-3 border-b-[0.5px] border-line px-5 py-3">
        <div className="min-w-0">
          <p className="truncate font-mono text-xs text-stone">
            {path}
            {lines ? `:${lines[0]}` : ""}
          </p>
          {heading && <h2 className="mt-0.5 truncate font-serif text-base text-clay">{heading}</h2>}
        </div>
        <Button onClick={copy} disabled={!path} aria-live="polite">
          {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
          {copied ? "Copied" : "Copy citation"}
        </Button>
      </header>
      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {win.isPending && <PreviewSkeleton />}
        {win.isError && <p className="text-sm text-danger">{win.error.message}</p>}
        {parts && (
          <pre className="whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-stone">
            {parts.before}
            <mark ref={markRef} className="block border-l-2 border-ochre bg-ochre-soft text-ink">
              {highlight(parts.match, terms)}
            </mark>
            {parts.after}
          </pre>
        )}
      </div>
    </article>
  );
}

export function PreviewSkeleton() {
  return (
    <div aria-hidden className="space-y-2">
      {[90, 75, 95, 60, 85].map((w, i) => (
        <div key={i} className="h-3 animate-pulse bg-sand" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}
