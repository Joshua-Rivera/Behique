"""Plain text, Markdown and source code."""

from __future__ import annotations

from pathlib import Path

from behique.extract import Document, register

# extension -> tree-sitter-language-pack language name
CODE_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "bash",
    ".lua": "lua",
}
PROSE_EXTS = (".txt", ".rst", ".text", ".log", ".csv", ".toml", ".yaml", ".yml", ".json", ".ini")


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    # Normalize newlines so offsets are stable across platforms.
    return text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")


@register(".md", ".markdown", ".mdx")
def markdown(path: Path) -> Document:
    return Document(read_text(path), "markdown")


@register(*PROSE_EXTS)
def prose(path: Path) -> Document:
    return Document(read_text(path), "prose")


@register(*CODE_LANGUAGES)
def code(path: Path) -> Document:
    return Document(read_text(path), "code", CODE_LANGUAGES[path.suffix.lower()])
