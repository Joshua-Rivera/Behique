"""PDF text via pypdf. Pages are separated by blank lines."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from behique.extract import Document, register


@register(".pdf")
def pdf(path: Path) -> Document:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return Document("\n\n".join(p for p in pages if p), "prose")
