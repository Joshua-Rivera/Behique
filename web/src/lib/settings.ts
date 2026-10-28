import { read, write } from "./storage";

export type SearchMode = "hybrid" | "vector" | "bm25";

export const MODES: { value: SearchMode; label: string }[] = [
  { value: "hybrid", label: "Hybrid" },
  { value: "vector", label: "Vector" },
  { value: "bm25", label: "Keyword" },
];
const KEY_NAME = "behique.apiKey";
const MODE_KEY = "behique.searchMode";

/** The API key lives in sessionStorage unless the user asks to remember it. */
export function getApiKey(): string {
  return read(KEY_NAME, "session") ?? read(KEY_NAME, "local") ?? "";
}

export function isKeyRemembered(): boolean {
  return read(KEY_NAME, "local") !== null;
}

export function setApiKey(key: string, remember: boolean): void {
  const value = key.trim() || null;
  write(KEY_NAME, remember ? null : value, "session");
  write(KEY_NAME, remember ? value : null, "local");
}

export function getDefaultMode(): SearchMode {
  const m = read(MODE_KEY);
  return m === "vector" || m === "bm25" ? m : "hybrid";
}

export function setDefaultMode(mode: SearchMode): void {
  write(MODE_KEY, mode === "hybrid" ? null : mode);
}
