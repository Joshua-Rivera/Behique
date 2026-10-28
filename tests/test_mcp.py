import json

from tests.test_api import _client, _wait

HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def _rpc(c, method, params=None, headers=None, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}
    return c.post("/mcp/", json=body, headers={**HEADERS, **(headers or {})})


def _init(c, headers=None):
    return _rpc(
        c,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
        headers,
    )


def _call(c, name, args, headers=None):
    r = _rpc(c, "tools/call", {"name": name, "arguments": args}, headers, id_=2)
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert not res.get("isError"), res
    if res.get("structuredContent") is not None:
        sc = res["structuredContent"]
        return sc.get("result", sc)
    return json.loads(res["content"][0]["text"])


def test_mcp_tools(tmp_path):
    c, svc, _ = _client(tmp_path)
    c.base_url = "http://localhost:8000"
    with c:
        c.post("/sources", json={"path": "notes"})
        c.post("/index")
        _wait(svc)
        assert _init(c).status_code == 200
        names = {t["name"] for t in _rpc(c, "tools/list").json()["result"]["tools"]}
        assert names == {"search_files", "read_file", "list_sources"}

        hits = _call(c, "search_files", {"query": "unique_token_xyz", "mode": "bm25"})
        assert hits[0]["path"] == "a.md"
        f = _call(c, "read_file", {"file_id": hits[0]["file_id"]})
        assert "unique_token_xyz" in f["text"]
        assert _call(c, "list_sources", {})[0]["files"] == 1


def test_mcp_without_trailing_slash(tmp_path):
    c, *_ = _client(tmp_path)
    c.base_url = "http://localhost:8000"
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    with c:
        r = c.post("/mcp", json=body, headers=HEADERS, follow_redirects=False)
        assert r.status_code == 200


def test_mcp_requires_key(tmp_path):
    c, *_ = _client(tmp_path, api_key="k")
    c.base_url = "http://localhost:8000"
    with c:
        assert _init(c).status_code == 401
        assert _init(c, {"x-api-key": "k"}).status_code == 200


def test_mcp_rejects_foreign_host(tmp_path):
    c, *_ = _client(tmp_path)
    c.base_url = "http://evil.example"
    with c:
        assert _init(c).status_code in (403, 421)
