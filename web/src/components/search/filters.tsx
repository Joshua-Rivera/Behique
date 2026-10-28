"use client";

import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover } from "@/components/ui/popover";
import { useSources } from "@/lib/api/hooks";

export type Filters = { source_id: number | null; ext: string; path_prefix: string };
export const NO_FILTERS: Filters = { source_id: null, ext: "", path_prefix: "" };

export function activeFilterCount(f: Filters) {
  return [f.source_id !== null, !!f.ext, !!f.path_prefix].filter(Boolean).length;
}

export function FilterPopover({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  const sources = useSources();
  const n = activeFilterCount(value);
  return (
    <Popover
      trigger={
        <Button tone={n ? "clay" : "stone"} aria-label={`Filters${n ? ` (${n} active)` : ""}`}>
          <SlidersHorizontal aria-hidden /> Filters{n ? ` · ${n}` : ""}
        </Button>
      }
    >
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-xs text-stone">
          Source
          <select
            value={value.source_id ?? ""}
            onChange={(e) =>
              onChange({ ...value, source_id: e.target.value ? Number(e.target.value) : null })
            }
            className="border-0 border-b-[0.5px] border-line bg-transparent py-1.5 text-sm text-ink focus:outline-none"
          >
            <option value="">All sources</option>
            {sources.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-stone">
          File type
          <Input
            value={value.ext}
            placeholder="md, py, pdf…"
            onChange={(e) => onChange({ ...value, ext: e.target.value.replace(/^\./, "").trim() })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-stone">
          Path prefix
          <Input
            value={value.path_prefix}
            placeholder="notes/"
            onChange={(e) => onChange({ ...value, path_prefix: e.target.value })}
          />
        </label>
        <Button tone="stone" onClick={() => onChange(NO_FILTERS)} disabled={!n} className="self-start">
          Clear filters
        </Button>
      </div>
    </Popover>
  );
}
