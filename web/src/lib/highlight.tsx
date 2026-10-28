import { Fragment, type ReactNode } from "react";

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const STOPWORDS = new Set(
  ("a an and are as at be but by can do does for from how i if in is it its my of on or so " +
    "that the their then there these this to was what when where which who why will with you your")
    .split(" "),
);

export function queryTerms(query: string): string[] {
  const words = query.toLowerCase().match(/[\p{L}\p{N}_]{2,}/gu) ?? [];
  return [...new Set(words.filter((w) => !STOPWORDS.has(w)))].sort((a, b) => b.length - a.length);
}

/** Wrap matched query terms in <mark>. Renders text nodes only, never HTML. */
export function highlight(text: string, terms: string[]): ReactNode {
  if (!terms.length) return text;
  // Match at word starts only, so "feed" marks "feeding" but "how" never marks "shows".
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])(${terms.map(escape).join("|")})`, "giu");
  return text.split(re).map((part, i) =>
    i % 2 === 1 ? <mark key={i}>{part}</mark> : <Fragment key={i}>{part}</Fragment>,
  );
}

/** 1-based line range of [start, end) within text. */
export function lineRange(text: string, start: number, end: number): [number, number] {
  const line = (pos: number) => text.slice(0, Math.max(0, pos)).split("\n").length;
  return [line(start), line(Math.max(start, end - 1))];
}

export function citation(path: string, lines: [number, number]): string {
  return lines[0] === lines[1] ? `${path}:${lines[0]}` : `${path}:${lines[0]}-${lines[1]}`;
}
