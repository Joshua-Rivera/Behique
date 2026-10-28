import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export function Checkbox({
  label,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2 text-sm text-ink", className)}>
      <input type="checkbox" className="size-3.5 cursor-pointer accent-[var(--clay)]" {...props} />
      {label}
    </label>
  );
}
