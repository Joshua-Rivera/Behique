"""Split Markdown at ATX headings, tracking the heading path (``A > B > C``)."""

from __future__ import annotations

import re

from behique.chunk import Section

_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$")
_FENCE = re.compile(r"^(```|~~~)")


def split(text: str) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []  # (level, title)
    start = 0
    current_path: str | None = None
    in_fence = False
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if _FENCE.match(stripped.lstrip()):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(stripped)
        if m:
            if text[start:pos].strip():
                sections.append(Section(start, pos, current_path))
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            current_path = " > ".join(t for _, t in stack)
            start = pos
        pos += len(line)
    if text[start:].strip():
        sections.append(Section(start, len(text), current_path))
    return sections
