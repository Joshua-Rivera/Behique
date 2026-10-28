import pytest

from behique.embed import DIM, Embedder
from behique.search import Filters, rrf_merge, search
from behique.store import ChunkRow, Store

DOCS = {
    "notes/cooking.md": "To bake sourdough bread, feed the starter and let it rise overnight.",
    "notes/travel.md": "The train from Lisbon to Porto takes about three hours along the coast.",
    "code/config.py": "def load_cfg_v2(path):\n    return yaml.safe_load(open(path))",
    "code/net.py": "def open_socket(host, port):\n    return socket.connect((host, port))",
    "docs/pets.txt": "Cats sleep for most of the day and enjoy warm sunny windows.",
}


@pytest.fixture(scope="module")
def emb():
    return Embedder()


@pytest.fixture(scope="module")
def idx(tmp_path_factory, emb):
    s = Store(tmp_path_factory.mktemp("s") / "s.db", emb.name, DIM)
    a = s.add_source("a", "/data/a")
    b = s.add_source("b", "/data/b")
    for i, (path, text) in enumerate(DOCS.items()):
        sid = a if path.startswith("notes") else b
        s.upsert_file(
            sid,
            path,
            size=len(text),
            mtime=1.0,
            content_hash=str(i),
            status="indexed",
            chunks=[ChunkRow(0, text, 0, len(text), 10)],
            embeddings=emb.embed_passages([text]),
        )
    return s, a, b


def test_rrf_merge_rewards_agreement():
    out = rrf_merge({"vector": [1, 2, 3], "bm25": [3, 4]}, k=4)
    assert out[0][0] == 3 and out[0][2] == ["vector", "bm25"]
    assert [c for c, _, _ in out] == [3, 1, 2, 4]


def test_bm25_finds_exact_identifier(idx, emb):
    s, *_ = idx
    hits = search(s, emb, "load_cfg_v2", k=3, mode="bm25")
    assert hits[0].path == "code/config.py"


def test_vector_finds_paraphrase(idx, emb):
    s, *_ = idx
    hits = search(s, emb, "how long is the rail journey between two Portuguese cities", 2, "vector")
    assert hits[0].path == "notes/travel.md"
    assert search(s, emb, "felines napping in sunlight", 1, "vector")[0].path == "docs/pets.txt"


def test_hybrid_combines_and_labels(idx, emb):
    s, *_ = idx
    hits = search(s, emb, "load_cfg_v2 yaml config", k=3)
    assert hits[0].path == "code/config.py"
    assert set(hits[0].retrievers) == {"vector", "bm25"}
    assert hits[0].text.startswith("def load_cfg_v2")


def test_filters(idx, emb):
    s, a, b = idx
    assert {h.source_id for h in search(s, emb, "bread", 5, filters=Filters(source_id=b))} == {b}
    assert all(h.path.endswith(".py") for h in search(s, emb, "x", 5, filters=Filters(ext="py")))
    hits = search(s, emb, "anything", 5, filters=Filters(path_prefix="notes/"))
    assert hits and all(h.path.startswith("notes/") for h in hits)
    assert search(s, emb, "x", 5, filters=Filters(path_prefix="no_such%")) == []


def test_empty_and_bad_mode(idx, emb):
    s, *_ = idx
    assert search(s, emb, "   ") == []
    assert search(s, emb, '"" (', mode="bm25") == []
    with pytest.raises(ValueError):
        search(s, emb, "x", mode="nope")
