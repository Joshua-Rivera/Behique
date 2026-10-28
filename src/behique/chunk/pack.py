"""Size sections to the token budget.

- Small adjacent sections with the same heading/symbol context are merged.
- Oversized sections are cut into windows of ``chunk_tokens`` with ``overlap``,
  ending on the best nearby boundary (blank line > newline > sentence > space).
- No chunk ever exceeds ``HARD_CAP`` tokens, the embedding model's limit minus
  its two special tokens.
"""

from __future__ import annotations

from behique import tokens
from behique.chunk import Chunk, Section
from behique.embed import MAX_TOKENS

HARD_CAP = MAX_TOKENS - 2  # [CLS] and [SEP]
_BOUNDARIES = ("\n\n", "\n", ". ", "? ", "! ", "; ", " ")


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _snap(text: str, lo: int, hi: int) -> int:
    """Best boundary position in text[lo:hi], preferring stronger boundaries near hi."""
    for sep in _BOUNDARIES:
        i = text.rfind(sep, lo, hi)
        if i != -1:
            return i + len(sep)
    return hi


def _window(text: str, sec: Section, budget: int, overlap: float) -> list[tuple[int, int]]:
    seg = text[sec.start : sec.end]
    offs = tokens.offsets(seg)
    n = len(offs)
    step_back = int(budget * overlap)
    spans = []
    i = 0
    while i < n:
        j = min(i + budget, n)
        s = sec.start + offs[i][0]
        if j == n:
            e = sec.end
        else:
            hard = sec.start + offs[j][0]  # start of first token that doesn't fit
            # Only snap within the last quarter so chunks stay near the budget.
            floor = sec.start + offs[i + (j - i) * 3 // 4][0]
            e = _snap(text, floor, hard)
        spans.append((s, e))
        if j == n:
            break
        # Next window starts at the first token at/after e, minus the overlap.
        k = i
        while k < n and sec.start + offs[k][0] < e:
            k += 1
        nxt = max(k - step_back, i + 1)
        i = nxt
    return spans


def _fit(text: str, s: int, e: int) -> list[tuple[int, int, int]]:
    """Guarantee the hard cap (boundary snapping can shift counts slightly)."""
    s, e = _trim(text, s, e)
    if s >= e:
        return []
    n = tokens.count(text[s:e])
    if n <= HARD_CAP:
        return [(s, e, n)]
    offs = tokens.offsets(text[s:e])
    cut = s + offs[HARD_CAP][0]
    return _fit(text, s, cut) + _fit(text, cut, e)


def pack(
    text: str, sections: list[Section], chunk_tokens: int = 400, overlap: float = 0.15
) -> list[Chunk]:
    budget = min(chunk_tokens, HARD_CAP)
    pieces: list[tuple[int, int, Section]] = []  # (start, end, context)
    for sec in sections:
        if tokens.count(text[sec.start : sec.end]) <= budget:
            pieces.append((sec.start, sec.end, sec))
        else:
            for s, e in _window(text, sec, budget, overlap):
                pieces.append((s, e, sec))

    # Merge small neighbours that share context and are contiguous.
    merged: list[tuple[int, int, Section]] = []
    for s, e, sec in pieces:
        if merged:
            ps, pe, psec = merged[-1]
            same = (psec.heading_path, psec.symbol) == (sec.heading_path, sec.symbol)
            if same and pe >= s and tokens.count(text[ps:e]) <= budget:
                merged[-1] = (ps, e, psec)
                continue
        merged.append((s, e, sec))

    out: list[Chunk] = []
    for s, e, sec in merged:
        for cs, ce, n in _fit(text, s, e):
            out.append(Chunk(text[cs:ce], cs, ce, n, sec.heading_path, sec.symbol))
    return out
