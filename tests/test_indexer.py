import os
import threading
import time

import pytest

from behique.config import Settings
from behique.indexer import Busy, Indexer
from behique.scan import denied, walk
from tests.conftest import DIM, rand_vec


class FakeEmbedder:
    def __init__(self):
        self.calls = 0
        self.gate: threading.Event | None = None

    def embed_passages(self, texts):
        if self.gate:
            self.gate.wait(5)
        self.calls += 1
        return [rand_vec(hash(t) % 1000, DIM) for t in texts]


@pytest.fixture
def setup(tmp_path, store):
    root = tmp_path / "src"
    root.mkdir()
    (root / "a.md").write_text("# A\nalpha text\n")
    (root / "b.py").write_text("def beta():\n    return 1\n")
    (root / ".env").write_text("SECRET=1\n")
    (root / "img.png").write_bytes(b"\x89PNG\0\0")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.js").write_text("x")
    (root / "bin.txt").write_bytes(b"ab\0cd")
    sid = store.add_source("src", str(root))
    emb = FakeEmbedder()
    settings = Settings(data_root=tmp_path, db_path=tmp_path / "t.db")
    return root, sid, emb, Indexer(store, emb, settings)


def test_deny_list():
    assert denied(".env") and denied(".env.local") and denied("id_rsa") and denied("x.PEM")
    assert not denied("notes.md")


def test_walk_skips_and_flags(setup):
    root, *_ = setup
    cands = {c.rel_path: c for c in walk(root, 1_000_000)}
    assert ".env" not in cands and "node_modules/x.js" not in cands
    assert cands["img.png"].skip_reason == "unsupported type"
    assert cands["bin.txt"].skip_reason == "binary"
    assert cands["a.md"].skip_reason is None


def test_initial_then_incremental(setup, store):
    root, sid, emb, idx = setup
    st = idx.run()
    assert st.files_changed == 4 and st.files_failed == 0 and st.files_skipped == 2
    files = store.files_for_source(sid)
    assert files["a.md"]["status"] == "indexed"
    assert files["img.png"]["status"] == "skipped"
    n_chunks = store.chunk_count()
    assert n_chunks >= 2

    # nothing changed
    st = idx.run()
    assert st.files_changed == 0 and st.files_seen == 4

    # touch without content change: no re-embed
    calls = emb.calls
    os.utime(root / "a.md", (time.time() + 10, time.time() + 10))
    assert idx.run().files_changed == 0 and emb.calls == calls

    # edit one file
    (root / "a.md").write_text("# A\nalpha text changed\n")
    st = idx.run()
    assert st.files_changed == 1
    assert store.fts_query("changed", 5)

    # delete one file
    (root / "b.py").unlink()
    st = idx.run()
    assert st.files_deleted == 1
    assert "b.py" not in store.files_for_source(sid)


def test_per_file_error_continues(setup, store, monkeypatch):
    root, sid, emb, idx = setup
    import behique.indexer as mod

    real = mod.extract

    def boom(path):
        if path.name == "a.md":
            raise RuntimeError("bad file")
        return real(path)

    monkeypatch.setattr(mod, "extract", boom)
    st = idx.run()
    assert st.files_failed == 1
    assert st.recent_errors[0]["path"] == "a.md"
    files = store.files_for_source(sid)
    assert files["a.md"]["status"] == "error" and files["b.py"]["status"] == "indexed"


def test_single_flight(setup):
    _, _, emb, idx = setup
    emb.gate = threading.Event()
    t = idx.start()
    with pytest.raises(Busy):
        idx.start()
    with pytest.raises(Busy):
        idx.run()
    emb.gate.set()
    t.join(5)
    assert not idx.running
    idx.run()  # usable again


def test_symlinks_not_followed(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("outside")
    (root / "link.md").symlink_to(outside)
    assert [c.rel_path for c in walk(root, 10_000)] == []
