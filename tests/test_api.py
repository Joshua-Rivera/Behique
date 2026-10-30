import time

import pytest
from fastapi.testclient import TestClient

from behique.config import Settings
from behique.main import _script_hashes, create_app
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


def _wait(svc, timeout=30.0):
    deadline = time.monotonic() + timeout
    while svc.indexer.running:
        assert time.monotonic() < deadline, "index run did not finish"
        time.sleep(0.02)


@pytest.fixture
def client(tmp_path):
    c, svc, data = _client(tmp_path)
    with c:
        yield c, svc, data


def test_full_flow(client):
    c, svc, _ = client
    h = c.get("/api/health").json()
    assert (h["ok"], h["model"], h["chunks"]) == (True, "fake", 0)
    r = c.post("/api/sources", json={"name": "notes", "path": "notes"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert c.post("/api/index", json={"source_id": sid}).status_code == 202
    _wait(svc)
    st = c.get("/api/index/status").json()
    assert st["running"] is False and st["files_changed"] == 1

    hits = c.post("/api/search", json={"query": "unique_token_xyz", "mode": "bm25"}).json()
    assert [h["path"] for h in hits] == ["a.md"]  # .env never indexed
    h = hits[0]
    assert h["retrievers"] == ["bm25"] and "unique_token_xyz" in h["text"]

    f = c.get(f"/api/files/{h['file_id']}").json()
    assert "unique_token_xyz" in f["text"]
    ch = c.get(
        f"/api/files/{h['file_id']}", params={"chunk_id": h["chunk_id"], "context": 1}
    ).json()
    assert ch["chunk_id"] == h["chunk_id"]
    assert c.get("/api/sources").json()[0]["files"] == 1


def test_source_validation(client):
    c, _, data = client
    assert c.post("/api/sources", json={"path": "/etc"}).status_code == 400
    assert c.post("/api/sources", json={"path": "../.."}).status_code == 400
    assert c.post("/api/sources", json={"path": "missing"}).status_code == 400
    assert c.post("/api/sources", json={"path": "notes"}).status_code == 201
    assert c.post("/api/sources", json={"path": str(data / "notes")}).status_code == 400  # dup


def test_index_conflict_and_404s(client):
    c, svc, _ = client
    c.post("/api/sources", json={"path": "notes"})
    assert c.post("/api/index", json={"source_id": 999}).status_code == 404
    assert svc.indexer._lock.acquire(blocking=False)
    try:
        assert c.post("/api/index").status_code == 409
        assert svc.rescan() is False
    finally:
        svc.indexer._lock.release()
    assert c.get("/api/files/12345").status_code == 404


def test_search_validation(client):
    c, *_ = client
    assert c.post("/api/search", json={"query": ""}).status_code == 422
    assert c.post("/api/search", json={"query": "x", "k": 0}).status_code == 422
    assert c.post("/api/search", json={"query": "x", "mode": "magic"}).status_code == 422


def test_api_key(tmp_path):
    c, *_ = _client(tmp_path, api_key="s3cret")
    with c:
        assert c.get("/api/health").status_code == 401
        assert c.get("/api/health", headers={"x-api-key": "nope"}).status_code == 401
        assert c.get("/api/health", headers={"x-api-key": "s3cret"}).status_code == 200
        assert c.get("/api/health", headers={"authorization": "Bearer s3cret"}).status_code == 200


def test_health_fields(client):
    c, *_ = client
    h = c.get("/api/health").json()
    assert h["version"] and h["ask_enabled"] is False and h["web_allowed"] is False


def test_static_ui_and_csp(tmp_path):
    web = tmp_path / "web"
    (web / "settings").mkdir(parents=True)
    (web / "index.html").write_text("<html><script>self.boot=1</script><body>ui</body></html>")
    (web / "settings" / "index.html").write_text("<html>settings</html>")
    settings = Settings(data_root=tmp_path, db_path=tmp_path / "db.sqlite", web_dir=web)
    svc = Service(settings, Store(settings.db_path, "fake", DIM), Emb())
    with TestClient(create_app(svc, rescan=False)) as c:
        r = c.get("/")
        assert r.status_code == 200 and "ui" in r.text
        csp = r.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in csp and "'sha256-" in csp
        assert "settings" in c.get("/settings/").text
        assert c.get("/api/health").json()["ok"] is True  # /api still wins over the UI
        assert "content-security-policy" in c.get("/api/health").headers


def test_script_hashes_match_loose_end_tags(tmp_path):
    (tmp_path / "index.html").write_text(
        "<script>a=1</script><script>b=2</script\t\n x><script src=/x.js></script>"
    )
    assert len(_script_hashes(tmp_path)) == 2


def test_dev_cors(tmp_path):
    settings = Settings(data_root=tmp_path, db_path=tmp_path / "db.sqlite", dev_cors=True)
    svc = Service(settings, Store(settings.db_path, "fake", DIM), Emb())
    with TestClient(create_app(svc, rescan=False)) as c:
        r = c.get("/api/health", headers={"origin": "http://localhost:3000"})
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
        r = c.get("/api/health", headers={"origin": "http://evil.example"})
        assert "access-control-allow-origin" not in r.headers


def test_mounts(client):
    c, _, data = client
    (data / "code").mkdir()
    (data / ".hidden").mkdir()
    (data / "file.txt").write_text("x")
    assert [m["name"] for m in c.get("/api/mounts").json()] == ["code", "notes"]
    c.post("/api/sources", json={"path": "notes"})
    assert {m["name"]: m["registered"] for m in c.get("/api/mounts").json()} == {
        "code": False,
        "notes": True,
    }
