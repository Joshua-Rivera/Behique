"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";
import type { Health } from "./types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => unwrap<Health>(api.GET("/api/health")),
    staleTime: 10_000,
  });
}
