"use client";

import { FolderPlus, Search as SearchIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { PageHeader } from "@/components/app-shell";
import { OPEN_SEARCH_EVENT } from "@/components/command-palette";
import { Preview, PreviewSkeleton, type PreviewTarget } from "@/components/preview/preview";
import { FilterPopover, NO_FILTERS, type Filters } from "@/components/search/filters";
import { Results } from "@/components/search/results";
import { Divider } from "@/components/ui/divider";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Tabs } from "@/components/ui/tabs";
import { useSearch, useSources } from "@/lib/api/hooks";
import type { Hit } from "@/lib/api/types";
import { useDebounced } from "@/lib/debounce";
import { queryTerms } from "@/lib/highlight";
import { useIsNarrow } from "@/lib/media";
import { usePaneSize } from "@/lib/resizable";
import { getDefaultMode, MODES, type SearchMode } from "@/lib/settings";

const PANE_MIN = 150;

function toTarget(h: Hit): PreviewTarget {
  return {
    fileId: h.file_id,
    chunkId: h.chunk_id,
    path: h.path,
    text: h.text,
    startChar: h.start_char,
    endChar: h.end_char,
  };
}

function Empty({ icon, title, children }: { icon: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
      <span className="text-stone [&_svg]:size-6">{icon}</span>
      <p className="font-serif text-lg text-ink">{title}</p>
      {children && <div className="max-w-sm text-sm text-stone">{children}</div>}
    </div>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [selected, setSelected] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const wanted = useRef<number | null>(null);
  const narrow = useIsNarrow();
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1000);
  const results = usePaneSize("results", {
    min: PANE_MIN,
    max: Math.max(PANE_MIN, width - PANE_MIN),
    initial: Math.round(width * 0.48),
  });

  useEffect(() => {
    setMode(getDefaultMode());
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    if (q) setQuery(q);
    const chunk = Number(params.get("chunk"));
    if (chunk) wanted.current = chunk;

    function onOpen(e: Event) {
      const { q, chunk } = (e as CustomEvent<{ q: string; chunk: number }>).detail;
      wanted.current = chunk;
      setQuery(q);
      setSelected(chunk);
    }
    window.addEventListener(OPEN_SEARCH_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_SEARCH_EVENT, onOpen);
  }, []);

  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => e && setWidth(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const debounced = useDebounced(query, 250);
  const sources = useSources();
  const search = useSearch({
    query: debounced,
    mode,
    source_id: filters.source_id,
    ext: filters.ext,
    path_prefix: filters.path_prefix,
  });
  const hits = useMemo(() => search.data ?? [], [search.data]);
  const terms = useMemo(() => queryTerms(debounced), [debounced]);

  useEffect(() => {
    if (wanted.current && hits.some((h) => h.chunk_id === wanted.current)) {
      setSelected(wanted.current);
      wanted.current = null;
    } else if (!hits.some((h) => h.chunk_id === selected)) setSelected(hits[0]?.chunk_id ?? null);
  }, [hits, selected]);

  // Keep the URL shareable without adding history entries.
  const loaded = useRef(false);
  useEffect(() => {
    if (!loaded.current) {
      loaded.current = true; // don't wipe ?q= before it has been read
      return;
    }
    const url = debounced.trim() ? `/?q=${encodeURIComponent(debounced.trim())}` : "/";
    window.history.replaceState(null, "", url);
  }, [debounced]);

  const hit = hits.find((h) => h.chunk_id === selected) ?? null;

  function onKeyDown(e: KeyboardEvent) {
    if (!hits.length) return;
    const i = hits.findIndex((h) => h.chunk_id === selected);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const next = e.key === "ArrowDown" ? Math.min(hits.length - 1, i + 1) : Math.max(0, i - 1);
      setSelected(hits[next]!.chunk_id);
    } else if (e.key === "Enter" && hit && narrow) {
      e.preventDefault();
      setSheetOpen(true);
    }
  }

  const noSources = sources.data?.length === 0;
  const body = (() => {
    if (noSources)
      return (
        <Empty icon={<FolderPlus />} title="No sources yet">
          Add a mounted folder on the <Link href="/sources/" className="text-clay underline">Sources</Link>{" "}
          page, then index it.
        </Empty>
      );
    if (!debounced.trim())
      return (
        <Empty icon={<SearchIcon />} title="Search your files">
          Hybrid mode mixes meaning and exact words. Use ↑/↓ to move through results.
        </Empty>
      );
    if (search.isError)
      return <p role="alert" className="px-4 py-6 text-sm text-danger">{search.error.message}</p>;
    if (search.isPending)
      return (
        <div className="p-4">
          <PreviewSkeleton />
        </div>
      );
    if (!hits.length)
      return (
        <Empty icon={<SearchIcon />} title="No results">
          Try other words, another mode, or clear the filters.
        </Empty>
      );
    return (
      <Results
        hits={hits}
        terms={terms}
        selected={selected}
        onSelect={(id) => {
          setSelected(id);
          if (narrow) setSheetOpen(true);
        }}
        onOpen={() => setSheetOpen(true)}
      />
    );
  })();

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Search" />
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-b-[0.5px] border-line px-6 py-3">
        <Input
          type="search"
          aria-label="Search your files"
          aria-controls="results-pane"
          aria-activedescendant={selected !== null ? `hit-${selected}` : undefined}
          placeholder="Search your files…"
          value={query}
          autoFocus
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          className="min-w-48 flex-1 text-base"
        />
        <Tabs label="Search mode" value={mode} options={MODES} onChange={setMode} />
        <FilterPopover value={filters} onChange={setFilters} />
      </div>
      <div ref={container} className="flex min-h-0 flex-1">
        <div
          id="results-pane"
          className="min-h-0 overflow-auto"
          style={narrow || !hit ? { flex: 1 } : { width: results.size, flexShrink: 0 }}
          aria-busy={search.isFetching}
        >
          {body}
        </div>
        {!narrow && hit && (
          <>
            <Divider
              label="Resize results and preview"
              size={results.size}
              min={PANE_MIN}
              max={Math.max(PANE_MIN, width - PANE_MIN)}
              onResize={results.setSize}
              onReset={results.reset}
            />
            <div className="min-h-0 min-w-[150px] flex-1">
              <Preview target={toTarget(hit)} terms={terms} />
            </div>
          </>
        )}
      </div>
      {narrow && hit && (
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen} title={hit.path} className="p-0">
          <Preview target={toTarget(hit)} terms={terms} />
        </Sheet>
      )}
    </div>
  );
}
