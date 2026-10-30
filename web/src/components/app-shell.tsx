"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { ApiError, UNAUTHORIZED_EVENT } from "@/lib/api/client";
import { useIsNarrow } from "@/lib/media";
import { usePaneSize } from "@/lib/resizable";
import { applyTheme, getTheme } from "@/lib/theme";

import { ZigzagBand } from "./motifs";
import { COMPACT_BELOW, Sidebar } from "./sidebar";
import { Divider } from "./ui/divider";
import { TooltipProvider } from "./ui/tooltip";

export const SIDEBAR = { min: 48, max: 240, initial: 140 };

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (n, err) => !(err instanceof ApiError && err.status < 500) && n < 2,
        refetchOnWindowFocus: false,
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(makeClient);
  return (
    <QueryClientProvider client={client}>
      <TooltipProvider delayDuration={300}>{children}</TooltipProvider>
    </QueryClientProvider>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const narrow = useIsNarrow();
  const sidebar = usePaneSize("sidebar", SIDEBAR);
  const width = narrow ? SIDEBAR.min : sidebar.size;

  useEffect(() => applyTheme(getTheme()), []);

  useEffect(() => {
    const onUnauthorized = () => {
      if (!window.location.pathname.startsWith("/settings")) router.push("/settings/?reason=auth");
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [router]);

  return (
    <div className="flex h-dvh overflow-hidden">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-surface focus:px-2 focus:text-clay"
      >
        Skip to content
      </a>
      <Sidebar width={width} compact={width < COMPACT_BELOW} />
      {narrow ? (
        <span aria-hidden className="w-[0.5px] shrink-0 bg-line" />
      ) : (
        <Divider
          label="Resize sidebar"
          size={sidebar.size}
          min={SIDEBAR.min}
          max={SIDEBAR.max}
          onResize={sidebar.setSize}
          onReset={sidebar.reset}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <ZigzagBand />
        <main id="main" className="min-h-0 flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b-[0.5px] border-line px-6 pb-3 pt-5">
      <h1 className="font-serif text-2xl text-clay">{title}</h1>
      {children}
    </header>
  );
}
