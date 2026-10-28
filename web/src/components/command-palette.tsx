"use client";

import { Command } from "cmdk";
import { FileText, MessageSquareText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useSearch } from "@/lib/api/hooks";
import { useDebounced } from "@/lib/debounce";
import { getDefaultMode } from "@/lib/settings";

import { NAV } from "./sidebar";

const item =
  "flex cursor-pointer items-center gap-2 border-l-2 border-transparent px-3 py-2 text-sm text-ink data-[selected=true]:border-ochre data-[selected=true]:bg-ochre-soft";

/** ⌘K / Ctrl+K: jump to a search result, ask about the query, or go to a page. */
export const OPEN_SEARCH_EVENT = "behique:open-search";

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query, 200);
  const search = useSearch({ query: open ? debounced : "", mode: getDefaultMode(), k: 8 });

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function go(href: string) {
    setOpen(false);
    setQuery("");
    router.push(href);
  }

  const q = query.trim();
  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Quick search"
      shouldFilter={false}
      overlayClassName="fixed inset-0 z-40 bg-black/30"
      contentClassName="fixed left-1/2 top-[15vh] z-50 w-[min(560px,calc(100vw-32px))] -translate-x-1/2 border-[0.5px] border-line bg-surface"
    >
      <Command.Input
        value={query}
        onValueChange={setQuery}
        placeholder="Search files or ask…"
        className="w-full border-0 border-b-[0.5px] border-line bg-transparent px-4 py-3 text-base text-ink placeholder:text-stone focus:outline-none"
      />
      <Command.List className="max-h-[50vh] overflow-auto py-1">
        {q && (
          <Command.Group heading="Ask" className="text-xs text-stone [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1">
            <Command.Item value="ask" onSelect={() => go(`/ask/?q=${encodeURIComponent(q)}`)} className={item}>
              <MessageSquareText className="size-4 text-clay" aria-hidden />
              Ask Behique about “{q}”
            </Command.Item>
          </Command.Group>
        )}
        {q && search.data && search.data.length > 0 && (
          <Command.Group heading="Results" className="text-xs text-stone [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1">
            {search.data.map((h) => (
              <Command.Item
                key={h.chunk_id}
                value={`hit-${h.chunk_id}`}
                onSelect={() => {
                  go(`/?q=${encodeURIComponent(q)}&chunk=${h.chunk_id}`);
                  // Already on Search: the page won't remount, so tell it directly.
                  window.dispatchEvent(
                    new CustomEvent(OPEN_SEARCH_EVENT, { detail: { q, chunk: h.chunk_id } }),
                  );
                }}
                className={item}
              >
                <FileText className="size-4 shrink-0 text-stone" aria-hidden />
                <span className="truncate font-mono text-xs">{h.path}</span>
                <span className="truncate text-stone">{h.heading_path || h.symbol}</span>
              </Command.Item>
            ))}
          </Command.Group>
        )}
        <Command.Group heading="Go to" className="text-xs text-stone [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Command.Item key={href} value={`nav-${label}`} onSelect={() => go(href)} className={item}>
              <Icon className="size-4 text-stone" aria-hidden />
              {label}
            </Command.Item>
          ))}
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
