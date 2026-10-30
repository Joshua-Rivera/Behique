"use client";

import { MessageSquareText, FolderTree, Search, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

import { IndexStatusLine } from "./index-status";
import { Logo } from "./motifs";
import { Tooltip } from "./ui/tooltip";

export const NAV = [
  { href: "/", label: "Search", icon: Search },
  { href: "/ask/", label: "Ask", icon: MessageSquareText },
  { href: "/sources/", label: "Sources", icon: FolderTree },
  { href: "/settings/", label: "Settings", icon: Settings },
] as const;

export const COMPACT_BELOW = 100;

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href.replace(/\/$/, ""));
}

export function Sidebar({ width, compact }: { width: number; compact: boolean }) {
  const pathname = usePathname() ?? "/";
  return (
    <aside
      style={{ width }}
      className="flex h-full shrink-0 flex-col overflow-hidden bg-sand"
      aria-label="Sidebar"
    >
      <div className={cn("flex h-12 items-center gap-2", compact ? "justify-center" : "px-4")}>
        <Logo />
        {!compact && <span className="font-serif text-lg text-clay">Behique</span>}
      </div>
      <nav aria-label="Main" className="mt-2 flex flex-col">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Tooltip key={href} content={label} disabled={!compact}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                aria-label={compact ? label : undefined}
                className={cn(
                  "flex items-center gap-2.5 border-l-2 py-2 text-sm transition-colors duration-150 ease-out",
                  compact ? "justify-center px-0" : "px-4",
                  active
                    ? "border-clay text-clay"
                    : "border-transparent text-stone hover:text-ink",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden />
                {!compact && <span className="truncate">{label}</span>}
              </Link>
            </Tooltip>
          );
        })}
      </nav>
      <div className={cn("mt-auto py-3", compact ? "flex justify-center" : "px-4")}>
        <IndexStatusLine compact={compact} />
      </div>
    </aside>
  );
}
