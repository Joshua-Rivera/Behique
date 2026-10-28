import { read, write } from "./storage";

export type Theme = "system" | "light" | "dark";
const KEY = "behique.theme";

export function getTheme(): Theme {
  const t = read(KEY);
  return t === "light" || t === "dark" ? t : "system";
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") root.removeAttribute("data-theme");
  else root.dataset.theme = theme;
}

export function setTheme(theme: Theme): void {
  write(KEY, theme === "system" ? null : theme);
  applyTheme(theme);
}
