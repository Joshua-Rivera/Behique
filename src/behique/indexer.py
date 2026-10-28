"""Index pipeline: scan -> diff -> extract -> chunk -> embed -> store.

One run at a time (single-flight lock). Per-file failures are recorded and the run
continues.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

from behique.chunk import chunk_document
from behique.config import Settings
from behique.extract import extract
from behique.scan import file_hash, walk
from behique.store import ChunkRow, Store

log = logging.getLogger(__name__)


@dataclass
class Status:
    running: bool = False
    started_at: float | None = None
    finished_at: float | None = None
    files_seen: int = 0
    files_changed: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    chunks_embedded: int = 0
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=20))

    def as_dict(self) -> dict:
        d = asdict(self)
        d["recent_errors"] = list(self.recent_errors)
        return d


class Busy(Exception):
    """An index run is already in progress."""


class Indexer:
    def __init__(self, store: Store, embedder, settings: Settings) -> None:
        self.store = store
        self.embedder = embedder
        self.settings = settings
        self._lock = threading.Lock()
        self.status = Status()

    @property
    def running(self) -> bool:
        return self._lock.locked()

    def start(self, source_id: int | None = None) -> threading.Thread:
        """Run in a background thread. Raises Busy if a run is in progress."""
        if not self._lock.acquire(blocking=False):
            raise Busy()
        t = threading.Thread(target=self._run_locked, args=(source_id,), daemon=True)
        t.start()
        return t

    def run(self, source_id: int | None = None) -> Status:
        """Run synchronously. Raises Busy if a run is in progress."""
        if not self._lock.acquire(blocking=False):
            raise Busy()
        self._run_locked(source_id)
        return self.status

    def _run_locked(self, source_id: int | None) -> None:
        self.status = Status(running=True, started_at=time.time())
        try:
            sources = self.store.list_sources()
            for src in sources:
                if source_id is None or src["id"] == source_id:
                    self._index_source(src["id"], Path(src["path"]))
        except Exception as exc:  # pragma: no cover - defensive
            log.exception("index run failed")
            self.status.recent_errors.append({"path": None, "error": repr(exc)})
        finally:
            self.status.running = False
            self.status.finished_at = time.time()
            self._lock.release()

    def _index_source(self, source_id: int, root: Path) -> None:
        known = self.store.files_for_source(source_id)
        seen: set[str] = set()
        if not root.is_dir():
            self.status.recent_errors.append({"path": str(root), "error": "source missing"})
            return
        for cand in walk(root, self.settings.max_file_bytes):
            seen.add(cand.rel_path)
            self.status.files_seen += 1
            prev = known.get(cand.rel_path)
            if prev is not None and prev["mtime"] == cand.mtime and prev["size"] == cand.size:
                continue
            try:
                digest = file_hash(cand.abs_path)
            except OSError as exc:
                self._fail(source_id, cand, "", exc)
                continue
            if prev is not None and prev["content_hash"] == digest:
                self.store.touch_file(prev["id"], cand.mtime)
                continue
            self.status.files_changed += 1
            meta = dict(size=cand.size, mtime=cand.mtime, content_hash=digest)
            if cand.skip_reason:
                self.status.files_skipped += 1
                self.store.upsert_file(
                    source_id, cand.rel_path, **meta, status="skipped", error=cand.skip_reason
                )
                continue
            try:
                doc = extract(cand.abs_path)
                chunks = chunk_document(doc, self.settings.chunk_tokens, self.settings.overlap)
                vectors = self.embedder.embed_passages([c.text for c in chunks]) if chunks else []
                rows = [
                    ChunkRow(
                        i, c.text, c.start_char, c.end_char, c.token_count, c.heading_path, c.symbol
                    )
                    for i, c in enumerate(chunks)
                ]
                self.store.upsert_file(
                    source_id,
                    cand.rel_path,
                    **meta,
                    status="indexed",
                    chunks=rows,
                    embeddings=vectors,
                )
                self.status.chunks_embedded += len(rows)
            except Exception as exc:
                self._fail(source_id, cand, digest, exc)

        for rel, row in known.items():
            if rel not in seen:
                self.store.delete_file(row["id"])
                self.status.files_deleted += 1

    def _fail(self, source_id: int, cand, digest: str, exc: Exception) -> None:
        log.warning("failed to index %s: %s", cand.rel_path, exc)
        self.status.files_failed += 1
        self.status.recent_errors.append({"path": cand.rel_path, "error": str(exc)[:500]})
        self.store.upsert_file(
            source_id,
            cand.rel_path,
            size=cand.size,
            mtime=cand.mtime,
            content_hash=digest,
            status="error",
            error=str(exc)[:500],
        )
