"""Vector, BM25 and hybrid (reciprocal rank fusion) search with metadata filters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from behique.store import Store, fts_query

Mode = Literal["hybrid", "vector", "bm25"]
RRF_K = 60  # standard RRF constant (Cormack et al., 2009)


@dataclass
class Filters:
    source_id: int | None = None
    ext: str | None = None  # ".md" or "md"
    path_prefix: str | None = None

    def sql(self) -> tuple[str, list]:
        clauses, args = [], []
        if self.source_id is not None:
            clauses.append("f.source_id = ?")
            args.append(self.source_id)
        if self.ext:
            ext = self.ext if self.ext.startswith(".") else "." + self.ext
            clauses.append("lower(f.rel_path) LIKE ? ESCAPE '\\'")
            args.append("%" + _like_escape(ext.lower()))
        if self.path_prefix:
            clauses.append("f.rel_path LIKE ? ESCAPE '\\'")
            args.append(_like_escape(self.path_prefix.lstrip("/")) + "%")
        return (" AND ".join(clauses) or "1"), args

    @property
    def active(self) -> bool:
        return any(v is not None and v != "" for v in (self.source_id, self.ext, self.path_prefix))


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass
class Hit:
    chunk_id: int
    file_id: int
    source_id: int
    path: str
    start_char: int
    end_char: int
    heading_path: str | None
    symbol: str | None
    score: float
    retrievers: list[str] = field(default_factory=list)
    text: str = ""


def _allowed(store: Store, ids: list[int], filters: Filters) -> set[int]:
    if not ids:
        return set()
    where, args = filters.sql()
    marks = ",".join("?" * len(ids))
    rows = store.conn.execute(
        f"SELECT c.id FROM chunks c JOIN files f ON f.id = c.file_id "
        f"WHERE c.id IN ({marks}) AND {where}",
        [*ids, *args],
    )
    return {r[0] for r in rows}


def vector_search(
    store: Store, query_vec: list[float], k: int, filters: Filters | None = None
) -> list[tuple[int, float]]:
    """(chunk_id, distance) nearest first, after filters."""
    filters = filters or Filters()
    if not filters.active:
        return store.vec_query(query_vec, k)
    # vec0 KNN can't join, so over-fetch and filter, widening until we have k.
    total = store.chunk_count()
    pool = k * 10
    while True:
        cands = store.vec_query(query_vec, min(pool, max(total, 1)))
        ok = _allowed(store, [c for c, _ in cands], filters)
        hits = [(c, d) for c, d in cands if c in ok]
        if len(hits) >= k or pool >= total:
            return hits[:k]
        pool *= 4


def bm25_search(
    store: Store, query: str, k: int, filters: Filters | None = None
) -> list[tuple[int, float]]:
    """(chunk_id, bm25) best first (bm25 is lower-is-better), after filters."""
    q = fts_query(query)
    if not q:
        return []
    where, args = (filters or Filters()).sql()
    rows = store.conn.execute(
        f"SELECT chunks_fts.rowid, bm25(chunks_fts) AS s FROM chunks_fts "
        f"JOIN chunks c ON c.id = chunks_fts.rowid JOIN files f ON f.id = c.file_id "
        f"WHERE chunks_fts MATCH ? AND {where} ORDER BY s LIMIT ?",
        [q, *args, k],
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def rrf_merge(
    ranked: dict[str, list[int]], k: int, rrf_k: int = RRF_K
) -> list[tuple[int, float, list[str]]]:
    """Fuse ranked id lists: score = sum 1/(rrf_k + rank). Ties keep first-seen order."""
    scores: dict[int, float] = {}
    found: dict[int, list[str]] = {}
    for name, ids in ranked.items():
        for rank, cid in enumerate(ids, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank)
            found.setdefault(cid, []).append(name)
    order = sorted(scores, key=lambda c: -scores[c])
    return [(c, scores[c], found[c]) for c in order[:k]]


def _hydrate(store: Store, scored: list[tuple[int, float, list[str]]]) -> list[Hit]:
    if not scored:
        return []
    ids = [c for c, _, _ in scored]
    marks = ",".join("?" * len(ids))
    rows = {
        r["id"]: r
        for r in store.conn.execute(
            f"SELECT c.*, f.rel_path, f.source_id FROM chunks c JOIN files f ON f.id = c.file_id "
            f"WHERE c.id IN ({marks})",
            ids,
        )
    }
    out = []
    for cid, score, retrievers in scored:
        r = rows.get(cid)
        if r is None:
            continue
        out.append(
            Hit(
                cid,
                r["file_id"],
                r["source_id"],
                r["rel_path"],
                r["start_char"],
                r["end_char"],
                r["heading_path"],
                r["symbol"],
                score,
                retrievers,
                r["text"],
            )
        )
    return out


def search(
    store: Store,
    embedder,
    query: str,
    k: int = 8,
    mode: Mode = "hybrid",
    filters: Filters | None = None,
) -> list[Hit]:
    if not query.strip() or k <= 0:
        return []
    filters = filters or Filters()
    pool = max(k * 4, 20)
    if mode == "vector":
        vec = vector_search(store, embedder.embed_query(query), k, filters)
        # Distances are L2 on unit vectors; report a similarity, higher is better.
        return _hydrate(store, [(c, 1.0 - d * d / 2.0, ["vector"]) for c, d in vec])
    if mode == "bm25":
        bm = bm25_search(store, query, k, filters)
        return _hydrate(store, [(c, -s, ["bm25"]) for c, s in bm])
    if mode != "hybrid":
        raise ValueError(f"unknown mode: {mode}")
    vec = vector_search(store, embedder.embed_query(query), pool, filters)
    bm = bm25_search(store, query, pool, filters)
    fused = rrf_merge({"vector": [c for c, _ in vec], "bm25": [c for c, _ in bm]}, k)
    return _hydrate(store, fused)
