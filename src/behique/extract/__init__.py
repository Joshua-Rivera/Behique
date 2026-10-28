"""Extractor registry: file extension -> function returning a Document."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Document:
    text: str
    kind: str  # "markdown" | "code" | "prose"
    language: str | None = None  # tree-sitter language name for code


class UnsupportedFile(Exception):
    pass


Extractor = Callable[[Path], Document]
_REGISTRY: dict[str, Extractor] = {}


def register(*exts: str) -> Callable[[Extractor], Extractor]:
    def deco(fn: Extractor) -> Extractor:
        for ext in exts:
            _REGISTRY[ext.lower()] = fn
        return fn

    return deco


def supported_extensions() -> set[str]:
    return set(_REGISTRY)


def extract(path: Path) -> Document:
    fn = _REGISTRY.get(path.suffix.lower())
    if fn is None:
        raise UnsupportedFile(f"unsupported extension: {path.suffix or '(none)'}")
    return fn(path)


from behique.extract import docx, pdf, text  # noqa: E402,F401  (register on import)
