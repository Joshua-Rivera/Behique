"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, FolderPlus, RefreshCw } from "lucide-react";
import { useEffect, useRef } from "react";

import { PageHeader } from "@/components/app-shell";
import { useIndexStatus } from "@/components/index-status";
import { AddSource } from "@/components/sources/add-source";
import { Button } from "@/components/ui/button";
import { api, ApiError, unwrap } from "@/lib/api/client";
import { useSources } from "@/lib/api/hooks";
import type { IndexStatus } from "@/lib/api/types";
import { ago } from "@/lib/time";

function Progress({ status }: { status: IndexStatus }) {
  const processed = status.files_changed + status.files_skipped + status.files_failed;
  return (
    <section aria-label="Index progress" className="border-b-[0.5px] border-line px-6 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
        <span className="text-moss" role="status" aria-live="polite">
          {status.running ? "Indexing…" : "Last run finished"}{" "}
          {status.finished_at && !status.running ? ago(status.finished_at) : ""}
        </span>
        <span className="text-stone">
          {status.files_seen} seen · {status.files_changed} changed · {status.files_deleted} removed ·{" "}
          {status.chunks_embedded} chunks embedded
          {status.files_failed ? (
            <span className="text-danger"> · {status.files_failed} failed</span>
          ) : null}
        </span>
      </div>
      {status.running && (
        <div className="mt-2 h-0.5 overflow-hidden bg-line" aria-hidden>
          <div
            className="h-full bg-moss transition-[width] duration-200 ease-out"
            style={{
              width: `${status.files_seen ? Math.max(4, (processed / status.files_seen) * 100) : 4}%`,
            }}
          />
        </div>
      )}
      {status.recent_errors.length > 0 && (
        <details className="group mt-3 text-sm">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1 text-danger">
            <ChevronRight
              className="size-4 transition-transform duration-150 group-open:rotate-90"
              aria-hidden
            />
            {status.recent_errors.length} recent errors
          </summary>
          <ul className="mt-2 space-y-1 border-l-2 border-danger pl-3">
            {status.recent_errors.map((e, i) => (
              <li key={i} className="font-mono text-xs text-stone">
                <span className="text-ink">{e.path ?? "index run"}</span>: {e.error}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

export default function SourcesPage() {
  const qc = useQueryClient();
  const sources = useSources();
  const status = useIndexStatus();
  const running = status.data?.running ?? false;

  const index = useMutation({
    mutationFn: (source_id: number | null) =>
      unwrap(api.POST("/api/index", { body: { source_id } })),
    onSettled: () => qc.invalidateQueries({ queryKey: ["index-status"] }),
  });

  // Refresh counts when a run ends.
  const wasRunning = useRef(running);
  useEffect(() => {
    if (wasRunning.current && !running) {
      qc.invalidateQueries({ queryKey: ["sources"] });
      qc.invalidateQueries({ queryKey: ["health"] });
      qc.invalidateQueries({ queryKey: ["search"] });
    }
    wasRunning.current = running;
  }, [running, qc]);

  const busy = running || index.isPending;
  const conflict = index.error instanceof ApiError && index.error.status === 409;

  return (
    <div>
      <PageHeader title="Sources">
        <div className="flex items-center gap-5">
          <Button onClick={() => index.mutate(null)} disabled={busy || !sources.data?.length}>
            <RefreshCw className={running ? "animate-spin" : undefined} aria-hidden /> Index now
          </Button>
          <AddSource />
        </div>
      </PageHeader>

      {index.isError && (
        <p role="alert" className="px-6 pt-3 text-sm text-danger">
          {conflict ? "An index run is already in progress." : index.error.message}
        </p>
      )}
      {status.data && (status.data.running || status.data.finished_at) && (
        <Progress status={status.data} />
      )}

      {sources.isPending && <p className="px-6 py-5 text-sm text-stone">Loading…</p>}
      {sources.isError && <p className="px-6 py-5 text-sm text-danger">{sources.error.message}</p>}
      {sources.data?.length === 0 && (
        <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
          <FolderPlus className="size-6 text-stone" aria-hidden />
          <p className="font-serif text-lg text-ink">No sources yet</p>
          <p className="max-w-sm text-sm text-stone">
            Pick a mounted folder with “Add source”. Behique only reads folders you mount.
          </p>
        </div>
      )}
      {sources.data && sources.data.length > 0 && (
        <div className="overflow-x-auto px-6">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b-[0.5px] border-line text-xs text-stone">
                <th className="py-2 font-normal">Name</th>
                <th className="py-2 text-right font-normal">Files</th>
                <th className="py-2 text-right font-normal">Chunks</th>
                <th className="py-2 pl-6 font-normal">Last indexed</th>
                <th className="py-2 font-normal">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sources.data.map((s) => (
                <tr key={s.id} className="border-b-[0.5px] border-line">
                  <td className="py-2.5">
                    <p className="text-ink">{s.name}</p>
                    <p className="font-mono text-xs text-stone">{s.path}</p>
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-moss">{s.files}</td>
                  <td className="py-2.5 text-right tabular-nums text-moss">{s.chunks}</td>
                  <td className="py-2.5 pl-6 text-stone">
                    {running && [null, s.id].includes(status.data?.source_id ?? null)
                      ? "Indexing…"
                      : ago(s.last_indexed_at)}
                  </td>
                  <td className="py-2.5 text-right">
                    <Button
                      tone="stone"
                      onClick={() => index.mutate(s.id)}
                      disabled={busy}
                      aria-label={`Index ${s.name} now`}
                    >
                      <RefreshCw aria-hidden /> Index
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
