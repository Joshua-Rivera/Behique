"""Walk a source folder and decide which files are candidates for indexing."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from behique.extract import supported_extensions

DENY_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".next",
    ".cache",
    ".ssh",
    ".gnupg",
    ".aws",
    ".terraform",
    "target",
}
# Secrets and noise. Matched against the file name, case-insensitively.
DENY_FILES = (
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    "*.kdbx",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials*",
    "*secret*",
    "*.lock",
    "package-lock.json",
    ".ds_store",
    "*.min.js",
    "*.map",
)
BINARY_OK = {".pdf", ".docx"}


@dataclass
class Candidate:
    rel_path: str
    abs_path: Path
    size: int
    mtime: float
    skip_reason: str | None = None


def denied(name: str) -> bool:
    lower = name.lower()
    return any(fnmatch.fnmatch(lower, pat) for pat in DENY_FILES)


def is_binary(path: Path, sniff: int = 8192) -> bool:
    with open(path, "rb") as f:
        return b"\0" in f.read(sniff)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def walk(root: Path, max_bytes: int) -> Iterator[Candidate]:
    """Yield every non-denied regular file under ``root``. Symlinks are never followed."""
    root = root.resolve()
    exts = supported_extensions()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in DENY_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.is_symlink() or denied(name):
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            rel = path.relative_to(root).as_posix()
            cand = Candidate(rel, path, st.st_size, st.st_mtime)
            ext = path.suffix.lower()
            if ext not in exts:
                cand.skip_reason = "unsupported type"
            elif st.st_size > max_bytes:
                cand.skip_reason = f"larger than {max_bytes} bytes"
            elif ext not in BINARY_OK and is_binary(path):
                cand.skip_reason = "binary"
            yield cand
