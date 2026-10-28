"""Structure-aware chunking.

Splitters cut a document into ``Section``s along its structure (headings, symbols,
paragraphs). ``pack`` then sizes those sections to the token budget. Every chunk's
text is exactly ``source[start_char:end_char]``.
"""

from __future__ import annotations

from dataclasses import dataclass

from behique.extract import Document


@dataclass
class Section:
    start: int
    end: int
    heading_path: str | None = None
    symbol: str | None = None


@dataclass
class Chunk:
    text: str
    start_char: int
    end_char: int
    token_count: int
    heading_path: str | None = None
    symbol: str | None = None


def chunk_document(doc: Document, chunk_tokens: int = 400, overlap: float = 0.15) -> list[Chunk]:
    from behique.chunk import code, markdown, pack, prose

    if doc.kind == "markdown":
        sections = markdown.split(doc.text)
    elif doc.kind == "code":
        sections = code.split(doc.text, doc.language or "")
    else:
        sections = prose.split(doc.text)
    return pack.pack(doc.text, sections, chunk_tokens=chunk_tokens, overlap=overlap)
