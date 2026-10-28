import pytest

from behique.store import ChunkRow, Store, fts_query
from tests.conftest import DIM, rand_vec


def _chunks(*texts):
    out, pos = [], 0
    for i, t in enumerate(texts):
        out.append(ChunkRow(i, t, pos, pos + len(t), len(t.split())))
        pos += len(t)
    return out


def test_round_trip_vec_and_fts(store):
    sid = store.add_source("notes", "/data/notes")
    chunks = _chunks("the quick brown fox", "parse_config reads yaml files")
    vecs = [rand_vec(1), rand_vec(2)]
    fid = store.upsert_file(
        sid,
        "a.md",
        size=10,
        mtime=1.0,
        content_hash="h",
        status="indexed",
        chunks=chunks,
        embeddings=vecs,
    )
    assert store.chunk_count() == 2
    ids = [r["id"] for r in store.chunks_for_file(fid)]

    hits = store.vec_query(rand_vec(2), k=2)
    assert hits[0][0] == ids[1]
    assert hits[0][1] < hits[1][1]

    fts = store.fts_query("parse_config", k=5)
    assert [h[0] for h in fts] == [ids[1]]


def test_reindex_replaces_chunks_fts_and_vec(store):
    sid = store.add_source("n", "/data/n")
    kw = dict(size=1, mtime=1.0, content_hash="h", status="indexed")
    store.upsert_file(sid, "a.md", **kw, chunks=_chunks("alpha"), embeddings=[rand_vec(1)])
    store.upsert_file(sid, "a.md", **kw, chunks=_chunks("beta"), embeddings=[rand_vec(2)])
    assert store.chunk_count() == 1
    assert store.fts_query("alpha", 5) == []
    assert len(store.fts_query("beta", 5)) == 1
    vec_rows = store.conn.execute("SELECT COUNT(*) FROM chunks_vec").fetchone()[0]
    assert vec_rows == 1


def test_delete_file_cleans_everything(store):
    sid = store.add_source("n", "/data/n")
    fid = store.upsert_file(
        sid,
        "a.md",
        size=1,
        mtime=1.0,
        content_hash="h",
        status="indexed",
        chunks=_chunks("gamma"),
        embeddings=[rand_vec(3)],
    )
    store.delete_file(fid)
    assert store.chunk_count() == 0
    assert store.fts_query("gamma", 5) == []
    assert store.conn.execute("SELECT COUNT(*) FROM chunks_vec").fetchone()[0] == 0


def test_failed_upsert_rolls_back(store):
    sid = store.add_source("n", "/data/n")
    with pytest.raises(ValueError):
        store.upsert_file(
            sid,
            "a.md",
            size=1,
            mtime=1.0,
            content_hash="h",
            status="indexed",
            chunks=_chunks("x"),
            embeddings=[[0.0] * (DIM + 1)],
        )
    assert store.files_for_source(sid) == {}
    assert store.chunk_count() == 0


def test_model_change_triggers_rebuild(tmp_path):
    path = tmp_path / "m.db"
    s = Store(path, "model-a", DIM)
    assert not s.rebuilt
    sid = s.add_source("n", "/data/n")
    s.upsert_file(
        sid,
        "a.md",
        size=1,
        mtime=1.0,
        content_hash="h",
        status="indexed",
        chunks=_chunks("delta"),
        embeddings=[rand_vec(4)],
    )
    s.close()
    assert not Store(path, "model-a", DIM).rebuilt
    s2 = Store(path, "model-b", 4)
    assert s2.rebuilt
    assert s2.chunk_count() == 0
    assert len(s2.list_sources()) == 1  # sources survive a rebuild


def test_list_sources_counts(store):
    sid = store.add_source("n", "/data/n")
    store.upsert_file(
        sid,
        "a.md",
        size=1,
        mtime=1.0,
        content_hash="h",
        status="indexed",
        chunks=_chunks("one", "two"),
        embeddings=[rand_vec(5), rand_vec(6)],
    )
    row = store.list_sources()[0]
    assert (row["file_count"], row["chunk_count"]) == (1, 2)


def test_fts_query_sanitizes():
    assert fts_query('foo "bar" NEAR(') == '"foo" OR "bar" OR "NEAR"'
    assert fts_query("  ") == ""


def test_store_memory():
    s = Store(":memory:", "m", DIM)
    assert s.chunk_count() == 0
