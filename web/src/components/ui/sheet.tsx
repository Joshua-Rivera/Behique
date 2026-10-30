"use client";

import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Side sheet: a flat panel separated by a hairline, over a plain dimmed backdrop. */
export function Sheet({
  open,
  onOpenChange,
  title,
  description,
  children,
  className,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <D.Content
          className={cn(
            "fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l-[0.5px] border-line bg-surface",
            "data-[state=open]:animate-[sheet-in_180ms_ease-out]",
            className,
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b-[0.5px] border-line px-5 py-4">
            <div>
              <D.Title className="font-serif text-lg text-clay">{title}</D.Title>
              {description ? (
                <D.Description className="mt-1 text-sm text-stone">{description}</D.Description>
              ) : (
                <D.Description className="sr-only">{title}</D.Description>
              )}
            </div>
            <D.Close className="cursor-pointer text-stone hover:text-ink" aria-label="Close">
              <X className="size-4" />
            </D.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-5 py-4">{children}</div>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}
