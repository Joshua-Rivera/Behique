"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, FolderPlus, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { api, unwrap } from "@/lib/api/client";
import { useMounts } from "@/lib/api/hooks";
import type { Source } from "@/lib/api/types";

const COMPOSE_SNIPPET = `services:
  behique:
    volumes:
      - ~/Documents/notes:/data/notes:ro`;

export function AddSource() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const mounts = useMounts(open);
  const add = useMutation({
    mutationFn: async (path: string) => {
      const src = await unwrap<Source>(api.POST("/api/sources", { body: { name: "", path } }));
      // Index the new source straight away; a running job just means it'll be picked up next.
      await api.POST("/api/index", { body: { source_id: src.id } });
      return src;
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["mounts"] });
      qc.invalidateQueries({ queryKey: ["sources"] });
      qc.invalidateQueries({ queryKey: ["index-status"] });
    },
  });

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <FolderPlus aria-hidden /> Add source
      </Button>
      <Sheet
        open={open}
        onOpenChange={setOpen}
        title="Add source"
        description="Folders mounted into the container under /data."
      >
        {mounts.isPending && <p className="text-sm text-stone">Loading…</p>}
        {mounts.isError && <p className="text-sm text-danger">{mounts.error.message}</p>}
        {mounts.data?.length === 0 && (
          <p className="text-sm text-stone">No folders are mounted under /data yet.</p>
        )}
        {mounts.data && mounts.data.length > 0 && (
          <ul className="border-t-[0.5px] border-line">
            {mounts.data.map((m) => (
              <li
                key={m.path}
                className="flex items-center justify-between gap-3 border-b-[0.5px] border-line py-2.5"
              >
                <div className="min-w-0">
                  <p className="text-sm text-ink">{m.name}</p>
                  <p className="truncate font-mono text-xs text-stone">{m.path}</p>
                </div>
                {m.registered ? (
                  <span className="inline-flex items-center gap-1 text-sm text-moss">
                    <Check className="size-4" aria-hidden /> Added
                  </span>
                ) : (
                  <Button
                    onClick={() => add.mutate(m.path)}
                    disabled={add.isPending}
                    aria-label={`Add ${m.name}`}
                  >
                    <Plus aria-hidden /> Add
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
        {add.isError && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {add.error.message}
          </p>
        )}
        <h3 className="mt-6 font-serif text-base text-ink">Don&apos;t see a folder?</h3>
        <p className="mt-1 text-sm text-stone">
          The container can only read folders you give it. Add a read-only mount under{" "}
          <code>/data</code> in <code>docker-compose.yml</code>, then run{" "}
          <code>docker compose up -d</code>:
        </p>
        <pre className="mt-3 overflow-auto border-l-2 border-ochre bg-sand px-3 py-2 font-mono text-xs text-ink">
          {COMPOSE_SNIPPET}
        </pre>
      </Sheet>
    </>
  );
}
