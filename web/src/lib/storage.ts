/** Browser storage that never throws (private windows, blocked site data, SSR). */

type Kind = "local" | "session";

function store(kind: Kind): Storage | null {
  try {
    if (typeof window === "undefined") return null;
    return kind === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

export function read(key: string, kind: Kind = "local"): string | null {
  try {
    return store(kind)?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function write(key: string, value: string | null, kind: Kind = "local"): void {
  try {
    const s = store(kind);
    if (!s) return;
    if (value === null) s.removeItem(key);
    else s.setItem(key, value);
  } catch {
    /* storage unavailable: keep working without it */
  }
}
