"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { SearchMode } from "../settings";
import { api, unwrap } from "./client";
import type { FileView, Health, Hit, Mount, Source } from "./types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => unwrap<Health>(api.GET("/api/health")),
    staleTime: 10_000,
  });
}

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: () => unwrap<Source[]>(api.GET("/api/sources")),
  });
}

export type SearchParams = {
  query: string;
  mode: SearchMode;
  k?: number;
  source_id?: number | null;
  ext?: string | null;
  path_prefix?: string | null;
};

export function useSearch(p: SearchParams) {
  const q = p.query.trim();
  return useQuery({
    queryKey: ["search", { ...p, query: q }],
    queryFn: ({ signal }) =>
      unwrap<Hit[]>(
        api.POST("/api/search", {
          body: {
            query: q,
            mode: p.mode,
            k: p.k ?? 20,
            source_id: p.source_id ?? null,
            ext: p.ext || null,
            path_prefix: p.path_prefix || null,
          },
          signal,
        }),
      ),
    enabled: q.length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useFileWindow(fileId: number | null, chunkId: number | null, context = 2) {
  return useQuery({
    queryKey: ["file", fileId, chunkId, context],
    queryFn: () =>
      unwrap<FileView>(
        api.GET("/api/files/{file_id}", {
          params: { path: { file_id: fileId! }, query: { chunk_id: chunkId, context } },
        }),
      ),
    enabled: fileId !== null,
  });
}

export function useFullFile(fileId: number | null) {
  return useQuery({
    queryKey: ["file", fileId, "full"],
    queryFn: () =>
      unwrap<FileView>(api.GET("/api/files/{file_id}", { params: { path: { file_id: fileId! } } })),
    enabled: fileId !== null,
    staleTime: 60_000,
  });
}

export function useMounts(enabled = true) {
  return useQuery({
    queryKey: ["mounts"],
    queryFn: () => unwrap<Mount[]>(api.GET("/api/mounts")),
    enabled,
  });
}
