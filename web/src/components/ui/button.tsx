import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Tone = "clay" | "stone" | "danger";

const tones: Record<Tone, string> = {
  clay: "text-clay",
  stone: "text-stone hover:text-ink",
  danger: "text-danger",
};

/** Flat text button: colored text plus icon, underlined on hover. No fill, border or shadow. */
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone }
>(function Button({ className, tone = "clay", type = "button", ...props }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center gap-1.5 bg-transparent p-0 text-sm font-medium underline-offset-4",
        "cursor-pointer rounded-sm hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline",
        "[&_svg]:size-4 [&_svg]:shrink-0",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
});
