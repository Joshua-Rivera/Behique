import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

/** A single bottom hairline instead of a box. */
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full border-0 border-b-[0.5px] border-line bg-transparent px-0 py-1.5 text-sm text-ink",
          "placeholder:text-stone focus:border-b-clay focus:outline-none focus-visible:outline-none",
          "transition-colors duration-150 ease-out",
          className,
        )}
        {...props}
      />
    );
  },
);
