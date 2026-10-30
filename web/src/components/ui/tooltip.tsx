"use client";

import * as T from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

export const TooltipProvider = T.Provider;

export function Tooltip({
  content,
  children,
  side = "right",
  disabled,
}: {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  disabled?: boolean;
}) {
  if (disabled) return <>{children}</>;
  return (
    <T.Root>
      <T.Trigger asChild>{children}</T.Trigger>
      <T.Portal>
        <T.Content
          side={side}
          sideOffset={6}
          className="z-50 border-[0.5px] border-line bg-sand px-2 py-1 text-xs text-ink"
        >
          {content}
        </T.Content>
      </T.Portal>
    </T.Root>
  );
}
