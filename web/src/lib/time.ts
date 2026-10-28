/** "3 min ago" style relative time for a Unix timestamp in seconds. */
export function ago(ts: number | null | undefined, now = Date.now()): string {
  if (!ts) return "Never";
  const s = Math.max(0, Math.round(now / 1000 - ts));
  if (s < 45) return "Just now";
  const units: [number, string][] = [
    [86400, "day"],
    [3600, "hour"],
    [60, "min"],
  ];
  for (const [size, name] of units) {
    if (s >= size) {
      const n = Math.round(s / size);
      return `${n} ${name}${n > 1 && name !== "min" ? "s" : ""} ago`;
    }
  }
  return "Just now";
}
