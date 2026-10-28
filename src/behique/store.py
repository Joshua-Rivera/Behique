"""SQLite store: files, chunks, FTS5 (BM25) and sqlite-vec vectors."""

from __future__ import annotations

import sqlite3
import struct
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import sqlite_vec

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('indexed', 'skipped', 'error')),
    error TEXT,
    indexed_at REAL NOT NULL,
    UNIQUE (source_id, rel_path)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    heading_path TEXT,
    symbol TEXT,
    UNIQUE (file_id, ordinal)
);
CREATE INDEX IF NOT EXISTS chunks_file ON chunks(file_id);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, content='chunks', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);

-- External-content FTS must be kept in sync by hand.
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    DELETE FROM chunks_vec WHERE rowid = old.id;
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE OF text ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


@dataclass
class ChunkRow:
    ordinal: int
    text: str
    start_char: int
    end_char: int
    token_count: int
    heading_path: str | None = None
    symbol: str | None = None


def _pack(vec: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 OR-query of quoted terms."""
    terms = ["".join(ch for ch in t if ch.isalnum() or ch == "_") for t in text.split()]
    return " OR ".join(f'"{t}"' for t in terms if t)


class Store:
    def __init__(self, path: str | Path, model_name: str, dim: int) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.dim = dim
        self.rebuilt = self._migrate(model_name, dim)

    # -- schema -----------------------------------------------------------

    def _migrate(self, model_name: str, dim: int) -> bool:
        """Create the schema. Returns True if a model change forced a rebuild."""
        c = self.conn
        c.executescript(_SCHEMA)
        meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
        rebuilt = bool(meta) and (meta.get("model") != model_name or meta.get("dim") != str(dim))
        with self.tx():
            if rebuilt:
                # Embeddings from another model are useless: drop all derived data.
                c.execute("DELETE FROM chunks")
                c.execute("DELETE FROM files")
                c.execute("DROP TABLE IF EXISTS chunks_vec")
            c.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(embedding float[{dim}])"
            )
            for key, value in (
                ("model", model_name),
                ("dim", str(dim)),
                ("schema_version", str(SCHEMA_VERSION)),
            ):
                c.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value))
        return rebuilt

    def tx(self):
        return _Tx(self.conn)

    # -- sources ----------------------------------------------------------

    def add_source(self, name: str, path: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO sources(name, path, created_at) VALUES (?, ?, ?)",
            (name, path, time.time()),
        )
        return cur.lastrowid

    def get_source(self, source_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()

    def list_sources(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT s.*,
                   COUNT(DISTINCT f.id) AS file_count,
                   COUNT(c.id) AS chunk_count,
                   MAX(f.indexed_at) AS last_indexed_at
            FROM sources s
            LEFT JOIN files f ON f.source_id = s.id
            LEFT JOIN chunks c ON c.file_id = f.id
            GROUP BY s.id ORDER BY s.id
            """
        ).fetchall()

    # -- files ------------------------------------------------------------

    def files_for_source(self, source_id: int) -> dict[str, sqlite3.Row]:
        rows = self.conn.execute("SELECT * FROM files WHERE source_id = ?", (source_id,))
        return {r["rel_path"]: r for r in rows}

    def get_file(self, file_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT f.*, s.path AS source_path, s.name AS source_name FROM files f "
            "JOIN sources s ON s.id = f.source_id WHERE f.id = ?",
            (file_id,),
        ).fetchone()

    def upsert_file(
        self,
        source_id: int,
        rel_path: str,
        *,
        size: int,
        mtime: float,
        content_hash: str,
        status: str,
        error: str | None = None,
        chunks: Sequence[ChunkRow] = (),
        embeddings: Sequence[Sequence[float]] = (),
    ) -> int:
        """Replace a file's row and all its chunks/fts/vec rows in one transaction."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        c = self.conn
        with self.tx():
            c.execute(
                """
                INSERT INTO files(source_id, rel_path, size, mtime, content_hash,
                                  status, error, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, rel_path) DO UPDATE SET
                    size = excluded.size, mtime = excluded.mtime,
                    content_hash = excluded.content_hash, status = excluded.status,
                    error = excluded.error, indexed_at = excluded.indexed_at
                """,
                (source_id, rel_path, size, mtime, content_hash, status, error, time.time()),
            )
            file_id = c.execute(
                "SELECT id FROM files WHERE source_id = ? AND rel_path = ?",
                (source_id, rel_path),
            ).fetchone()[0]
            c.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            for ch, emb in zip(chunks, embeddings, strict=True):
                if len(emb) != self.dim:
                    raise ValueError(f"embedding has dim {len(emb)}, expected {self.dim}")
                cid = c.execute(
                    """
                    INSERT INTO chunks(file_id, ordinal, text, start_char, end_char,
                                       token_count, heading_path, symbol)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        ch.ordinal,
                        ch.text,
                        ch.start_char,
                        ch.end_char,
                        ch.token_count,
                        ch.heading_path,
                        ch.symbol,
                    ),
                ).lastrowid
                c.execute(
                    "INSERT INTO chunks_vec(rowid, embedding) VALUES (?, ?)", (cid, _pack(emb))
                )
        return file_id

    def touch_file(self, file_id: int, mtime: float) -> None:
        """Content unchanged but mtime moved: record the new mtime only."""
        self.conn.execute("UPDATE files SET mtime = ? WHERE id = ?", (mtime, file_id))

    def delete_file(self, file_id: int) -> None:
        with self.tx():
            self.conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            self.conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

    # -- chunks -----------------------------------------------------------

    def chunk_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def get_chunk(self, chunk_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()

    def chunks_for_file(self, file_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM chunks WHERE file_id = ? ORDER BY ordinal", (file_id,)
        ).fetchall()

    # -- queries ----------------------------------------------------------

    def vec_query(self, embedding: Sequence[float], k: int) -> list[tuple[int, float]]:
        """(chunk_id, L2 distance) nearest first (normalized vectors: same order as cosine)."""
        rows = self.conn.execute(
            "SELECT rowid, distance FROM chunks_vec WHERE embedding MATCH ? AND k = ? "
            "ORDER BY distance",
            (_pack(embedding), k),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def fts_query(self, text: str, k: int) -> list[tuple[int, float]]:
        """(chunk_id, bm25) best first. bm25() is lower-is-better."""
        q = fts_query(text)
        if not q:
            return []
        rows = self.conn.execute(
            "SELECT rowid, bm25(chunks_fts) AS score FROM chunks_fts WHERE chunks_fts MATCH ? "
            "ORDER BY score LIMIT ?",
            (q, k),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def close(self) -> None:
        self.conn.close()


class _Tx:
    """Reentrant BEGIN/COMMIT around an autocommit connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.owner = False

    def __enter__(self):
        if not self.conn.in_transaction:
            self.conn.execute("BEGIN IMMEDIATE")
            self.owner = True
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        if self.owner:
            self.conn.execute("ROLLBACK" if exc_type else "COMMIT")
        return False
