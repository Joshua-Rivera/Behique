"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { IndexStatus } from "@/lib/api/types";
import { cn } from "@/lib/cn";

export function useIndexStatus() {
  return useQuery({
    queryKey: ["index-status"],
    queryFn: () => unwrap<IndexStatus>(api.GET("/api/index/status")),
    refetchInterval: (q) => (q.state.data?.running ? 1000 : 5000),
  });
}

export function statusLabel(s: IndexStatus | undefined): { text: string; tone: "moss" | "danger" | "stone" } {
  if (!s) return { text: "Connecting…", tone: "stone" };
  if (s.running) {
    return { text: `Indexing · ${s.files_seen} files`, tone: "moss" };
  }
  if (s.files_failed) return { text: `${s.files_failed} errors`, tone: "danger" };
  return { text: "Idle", tone: "moss" };
}

export function IndexStatusLine({ compact }: { compact: boolean }) {
  const { data, isError } = useIndexStatus();
  const { text, tone } = isError ? { text: "Offline", tone: "danger" as const } : statusLabel(data);
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex items-center gap-2 text-xs", {
        "text-moss": tone === "moss",
        "text-danger": tone === "danger",
        "text-stone": tone === "stone",
      })}
      title={text}
    >
      <span
        aria-hidden
        className={cn("size-1.5 shrink-0 rounded-full bg-current", data?.running && "animate-pulse")}
      />
      <span className={cn(compact && "sr-only")}>{text}</span>
    </div>
  );
}
