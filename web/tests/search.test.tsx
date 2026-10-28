import { render } from "@testing-library/react";

import { groupByFile } from "@/components/search/results";
import type { Hit } from "@/lib/api/types";
import { citation, highlight, lineRange, queryTerms } from "@/lib/highlight";

const hit = (chunk_id: number, file_id: number, path: string): Hit => ({
  chunk_id,
  file_id,
  source_id: 1,
  path,
  start_char: 0,
  end_char: 1,
  heading_path: null,
  symbol: null,
  score: 1,
  retrievers: ["bm25"],
  text: "",
});

test("query terms are unique, lowercased and longest first", () => {
  expect(queryTerms("Retry retry_with_backoff a")).toEqual(["retry_with_backoff", "retry"]);
});

test("highlight wraps matches in mark and escapes regex characters", () => {
  const { container } = render(<p>{highlight("call foo(x) then FOO", ["foo(x)", "foo"])}</p>);
  expect([...container.querySelectorAll("mark")].map((m) => m.textContent)).toEqual(["foo(x)", "FOO"]);
});

test("highlight never renders markup from the text", () => {
  const { container } = render(<p>{highlight("<img src=x onerror=alert(1)> img", ["img"])}</p>);
  expect(container.querySelector("img")).toBeNull();
});

test("line ranges and citations", () => {
  const text = "a\nb\nc\nd";
  expect(lineRange(text, 2, 5)).toEqual([2, 3]);
  expect(citation("x.md", [2, 3])).toBe("x.md:2-3");
  expect(citation("x.md", [4, 4])).toBe("x.md:4");
});

test("results group by file in rank order", () => {
  const groups = groupByFile([hit(1, 10, "a"), hit(2, 20, "b"), hit(3, 10, "a")]);
  expect(groups.map((g) => [g.path, g.hits.map((h) => h.chunk_id)])).toEqual([
    ["a", [1, 3]],
    ["b", [2]],
  ]);
});
