"use client";

import { Globe } from "lucide-react";
import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

import type { Citation } from "@/lib/api/types";

type Local = Extract<Citation, { type: "local" }>;
type Web = Extract<Citation, { type: "web" }>;

const CHUNK_REF = /\[chunk:(\d+)\]/g;

/** Turn `[chunk:N]` markers into numbered `#cite-N` links; unknown chunks are dropped. */
export function linkCitations(answer: string, citations: Citation[]): string {
  const order = citations
    .filter((c): c is Local => c.type === "local")
    .map((c) => c.chunk_id);
  return answer.replace(CHUNK_REF, (_, id: string) => {
    const n = order.indexOf(Number(id));
    return n < 0 ? "" : `[${n + 1}](#cite-${id})`;
  });
}

const chip =
  "mx-0.5 cursor-pointer border-b border-dotted align-baseline text-[0.8em] font-sans tabular-nums";

export function Answer({
  text,
  citations,
  onOpenLocal,
}: {
  text: string;
  citations: Citation[];
  onOpenLocal: (c: Local) => void;
}) {
  const locals = new Map(
    citations.filter((c): c is Local => c.type === "local").map((c) => [c.chunk_id, c]),
  );
  const webs = citations.filter((c): c is Web => c.type === "web");

  function A({ href = "", children }: ComponentProps<"a">) {
    const m = href.match(/^#cite-(\d+)$/);
    const local = m ? locals.get(Number(m[1])) : undefined;
    if (local)
      return (
        <button
          type="button"
          onClick={() => onOpenLocal(local)}
          className={`${chip} border-clay text-clay`}
          title={local.path}
          aria-label={`Source ${children}: ${local.path}`}
        >
          {children}
        </button>
      );
    if (/^https?:\/\//i.test(href))
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-sea underline">
          {children}
        </a>
      );
    return <span>{children}</span>;
  }

  return (
    <div>
      <div className="prose-behique font-serif text-[17px] leading-relaxed text-ink">
        <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={{ a: A }}>
          {linkCitations(text, citations)}
        </ReactMarkdown>
      </div>
      {(locals.size > 0 || webs.length > 0) && (
        <ol className="mt-4 flex flex-col gap-1 border-t-[0.5px] border-line pt-3 text-sm">
          {[...locals.values()].map((c, i) => (
            <li key={`l${c.chunk_id}`} className="flex gap-2">
              <span className="w-5 shrink-0 text-right tabular-nums text-clay">{i + 1}</span>
              <button
                type="button"
                onClick={() => onOpenLocal(c)}
                className="min-w-0 cursor-pointer truncate text-left font-mono text-xs text-clay hover:underline"
              >
                {c.path}
                {c.heading_path ? ` · ${c.heading_path}` : ""}
              </button>
            </li>
          ))}
          {webs.map((c) => (
            <li key={c.url} className="flex gap-2">
              <Globe className="mt-0.5 size-3.5 w-5 shrink-0 text-sea" aria-hidden />
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-0 truncate text-xs text-sea underline decoration-dotted"
              >
                {c.title || c.url}
              </a>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
