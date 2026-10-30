/** Abstract motifs inspired by Taíno art: concentric rings and a zigzag band. */

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden focusable="false">
      <circle cx="12" cy="12" r="10.5" fill="none" stroke="var(--clay)" strokeWidth="2" />
      <circle cx="12" cy="12" r="6.5" fill="none" stroke="var(--ochre)" strokeWidth="2" />
      <circle cx="12" cy="12" r="2.5" fill="var(--moss)" />
    </svg>
  );
}

export function ZigzagBand() {
  return (
    <svg
      className="block h-1.5 w-full"
      preserveAspectRatio="none"
      viewBox="0 0 120 6"
      aria-hidden
      focusable="false"
    >
      <defs>
        <pattern id="zigzag" width="12" height="6" patternUnits="userSpaceOnUse">
          <path d="M0 5 L3 1 L6 5 L9 1 L12 5" fill="none" stroke="var(--ochre)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="120" height="6" fill="url(#zigzag)" />
    </svg>
  );
}
