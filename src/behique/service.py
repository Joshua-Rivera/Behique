"""The service layer. REST, MCP and /ask are thin clients over this class."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from behique.config import Settings
from behique.indexer import Busy, Indexer
from behique.search import Filters, Mode, search
from behique.store import Store

log = logging.getLogger(__name__)


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


class Service:
    def __init__(self, settings: Settings, store: Store, embedder) -> None:
        self.settings = settings
        self.store = store
        self.embedder = embedder
        self.indexer = Indexer(store, embedder, settings)

    # -- health / sources -------------------------------------------------

    def health(self) -> dict:
        return {"ok": True, "model": self.embedder.name, "chunks": self.store.chunk_count()}

    def add_source(self, name: str, path: str) -> dict:
        root = self.settings.data_root.resolve()
        raw = Path(path)
        target = (raw if raw.is_absolute() else root / raw).resolve()
        if not target.is_relative_to(root):
            raise BadRequest(f"path must be inside {root}")
        if not target.is_dir():
            raise BadRequest(f"not a directory: {target}")
        if any(s["path"] == str(target) for s in self.store.list_sources()):
            raise BadRequest("source already registered")
        sid = self.store.add_source(name.strip() or target.name, str(target))
        return self._source_dict(next(s for s in self.store.list_sources() if s["id"] == sid))

    def list_sources(self) -> list[dict]:
        return [self._source_dict(s) for s in self.store.list_sources()]

    @staticmethod
    def _source_dict(row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "path": row["path"],
            "files": row["file_count"],
            "chunks": row["chunk_count"],
            "last_indexed_at": row["last_indexed_at"],
        }

    # -- indexing ---------------------------------------------------------

    def start_index(self, source_id: int | None = None) -> dict:
        if source_id is not None and self.store.get_source(source_id) is None:
            raise NotFound(f"source {source_id} not found")
        self.indexer.start(source_id)  # raises Busy
        return {"started": True, "source_id": source_id}

    def rescan(self) -> bool:
        """Periodic rescan. Skips its turn if a run is in progress."""
        try:
            self.indexer.start()
        except Busy:
            return False
        return True

    def index_status(self) -> dict:
        return self.indexer.status.as_dict()

    # -- search / read ----------------------------------------------------

    def search(
        self,
        query: str,
        k: int = 8,
        mode: Mode = "hybrid",
        source_id: int | None = None,
        ext: str | None = None,
        path_prefix: str | None = None,
    ) -> list[dict]:
        if not 1 <= k <= 50:
            raise BadRequest("k must be between 1 and 50")
        hits = search(
            self.store, self.embedder, query, k, mode, Filters(source_id, ext, path_prefix)
        )
        return [asdict(h) for h in hits]

    def read_file(self, file_id: int, chunk_id: int | None = None, context: int = 1) -> dict:
        """File text, or a chunk with ``context`` neighbours each side. Ids only, never paths."""
        f = self.store.get_file(file_id)
        if f is None or f["status"] != "indexed":
            raise NotFound(f"file {file_id} not found")
        chunks = self.store.chunks_for_file(file_id)
        base = {"file_id": file_id, "source_id": f["source_id"], "path": f["rel_path"]}
        if chunk_id is None:
            return {**base, "text": self._full_text(chunks), "chunks": len(chunks)}
        context = max(0, min(context, 5))
        pos = next((i for i, c in enumerate(chunks) if c["id"] == chunk_id), None)
        if pos is None:
            raise NotFound(f"chunk {chunk_id} not in file {file_id}")
        window = chunks[max(0, pos - context) : pos + context + 1]
        return {
            **base,
            "chunk_id": chunk_id,
            "text": self._full_text(window),
            "start_char": window[0]["start_char"],
            "end_char": window[-1]["end_char"],
            "heading_path": chunks[pos]["heading_path"],
            "symbol": chunks[pos]["symbol"],
        }

    @staticmethod
    def _full_text(chunks) -> str:
        """Stitch chunks back together, dropping the overlap between neighbours."""
        out, end = [], 0
        for c in chunks:
            text, start = c["text"], c["start_char"]
            if out and start < end:
                text = text[end - start :]
            elif out:
                text = "\n" + text if not text.startswith("\n") else text
            out.append(text)
            end = max(end, c["end_char"])
        return "".join(out)

    def chunk_location(self, chunk_id: int) -> dict:
        c = self.store.get_chunk(chunk_id)
        if c is None:
            raise NotFound(f"chunk {chunk_id} not found")
        return {"chunk_id": chunk_id, "file_id": c["file_id"]}


def build_service(settings: Settings | None = None) -> Service:
    from behique.embed import Embedder

    settings = settings or Settings()
    embedder = Embedder(settings.model_cache)
    store = Store(settings.db_path, embedder.name, embedder.dim)
    if store.rebuilt:
        log.warning("embedding model changed: index rebuilt")
    return Service(settings, store, embedder)
