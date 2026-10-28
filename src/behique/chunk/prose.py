"""Prose has no structure beyond paragraphs, which the packer already respects."""

from __future__ import annotations

from behique.chunk import Section


def split(text: str) -> list[Section]:
    return [Section(0, len(text))] if text.strip() else []
