"use client";

import * as P from "@radix-ui/react-popover";
import type { ReactNode } from "react";

export function Popover({ trigger, children }: { trigger: ReactNode; children: ReactNode }) {
  return (
    <P.Root>
      <P.Trigger asChild>{trigger}</P.Trigger>
      <P.Portal>
        <P.Content
          align="end"
          sideOffset={8}
          className="z-50 w-72 border-[0.5px] border-line bg-surface p-4 text-sm"
        >
          {children}
        </P.Content>
      </P.Portal>
    </P.Root>
  );
}
