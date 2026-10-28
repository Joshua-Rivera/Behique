import time

import pytest
from fastapi.testclient import TestClient

from behique.config import Settings
from behique.main import create_app
from behique.service import Service
from behique.store import Store
from tests.conftest import DIM
from tests.test_indexer import FakeEmbedder


class Emb(FakeEmbedder):
    name = "fake"
    dim = DIM

    def embed_query(self, q):
        return self.embed_passages([q])[0]


def _client(tmp_path, api_key=None):
    data = tmp_path / "data"
    (data / "notes").mkdir(parents=True)
    (data / "notes" / "a.md").write_text("# Title\nunique_token_xyz lives here\n\n## Two\nsecond\n")
    (data / "notes" / ".env").write_text("TOKEN=unique_token_xyz\n")
    settings = Settings(data_root=data, db_path=tmp_path / "db.sqlite", api_key=api_key)
    svc = Service(settings, Store(settings.db_path, "fake", DIM), Emb())
    return TestClient(create_app(svc, rescan=False)), svc, data


def _wait(svc):
    for _ in range(200):
        if not svc.indexer.running:
            return
        time.sleep(0.01)


@pytest.fixture
def client(tmp_path):
    c, svc, data = _client(tmp_path)
    with c:
        yield c, svc, data


def test_full_flow(client):
    c, svc, _ = client
    assert c.get("/health").json() == {"ok": True, "model": "fake", "chunks": 0}
    r = c.post("/sources", json={"name": "notes", "path": "notes"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert c.post("/index", json={"source_id": sid}).status_code == 202
    _wait(svc)
    st = c.get("/index/status").json()
    assert st["running"] is False and st["files_changed"] == 1

    hits = c.post("/search", json={"query": "unique_token_xyz", "mode": "bm25"}).json()
    assert [h["path"] for h in hits] == ["a.md"]  # .env never indexed
    h = hits[0]
    assert h["retrievers"] == ["bm25"] and "unique_token_xyz" in h["text"]

    f = c.get(f"/files/{h['file_id']}").json()
    assert "unique_token_xyz" in f["text"]
    ch = c.get(f"/files/{h['file_id']}", params={"chunk_id": h["chunk_id"], "context": 1}).json()
    assert ch["chunk_id"] == h["chunk_id"]
    assert c.get("/sources").json()[0]["files"] == 1


def test_source_validation(client):
    c, _, data = client
    assert c.post("/sources", json={"path": "/etc"}).status_code == 400
    assert c.post("/sources", json={"path": "../.."}).status_code == 400
    assert c.post("/sources", json={"path": "missing"}).status_code == 400
    assert c.post("/sources", json={"path": "notes"}).status_code == 201
    assert c.post("/sources", json={"path": str(data / "notes")}).status_code == 400  # dup


def test_index_conflict_and_404s(client):
    c, svc, _ = client
    c.post("/sources", json={"path": "notes"})
    assert c.post("/index", json={"source_id": 999}).status_code == 404
    assert svc.indexer._lock.acquire(blocking=False)
    try:
        assert c.post("/index").status_code == 409
        assert svc.rescan() is False
    finally:
        svc.indexer._lock.release()
    assert c.get("/files/12345").status_code == 404


def test_search_validation(client):
    c, *_ = client
    assert c.post("/search", json={"query": ""}).status_code == 422
    assert c.post("/search", json={"query": "x", "k": 0}).status_code == 422
    assert c.post("/search", json={"query": "x", "mode": "magic"}).status_code == 422


def test_api_key(tmp_path):
    c, *_ = _client(tmp_path, api_key="s3cret")
    with c:
        assert c.get("/health").status_code == 401
        assert c.get("/health", headers={"x-api-key": "nope"}).status_code == 401
        assert c.get("/health", headers={"x-api-key": "s3cret"}).status_code == 200
        assert c.get("/health", headers={"authorization": "Bearer s3cret"}).status_code == 200
