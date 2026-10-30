import { fireEvent, render, screen } from "@testing-library/react";

import { Answer, linkCitations } from "@/components/ask/answer";
import { parseBlock } from "@/lib/api/sse";
import type { Citation } from "@/lib/api/types";

const cites: Citation[] = [
  { type: "local", chunk_id: 7, file_id: 1, path: "notes/a.md" },
  { type: "web", url: "https://example.com/x", title: "Example" },
];

test("parses SSE blocks", () => {
  expect(parseBlock('event: step\ndata: {"kind":"search"}')).toEqual({
    event: "step",
    data: { kind: "search" },
  });
  expect(parseBlock(": comment")).toBeNull();
});

test("chunk markers become numbered links, unknown ones vanish", () => {
  expect(linkCitations("A [chunk:7] B [chunk:9].", cites)).toBe("A [1](#cite-7) B .");
});

test("answer renders chips, web links and no raw HTML", () => {
  const open = vi.fn();
  const { container } = render(
    <Answer
      text={'Yes [chunk:7]. <img src=x onerror="alert(1)"> [link](javascript:alert(1))'}
      citations={cites}
      onOpenLocal={open}
    />,
  );
  expect(container.querySelector("img")).toBeNull();
  expect(container.querySelector('a[href^="javascript"]')).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /Source 1: notes\/a\.md/ }));
  expect(open).toHaveBeenCalledWith(cites[0]);
  const web = screen.getByRole("link", { name: "Example" });
  expect(web).toHaveAttribute("target", "_blank");
  expect(web).toHaveAttribute("rel", "noopener noreferrer");
});
