import json
import threading
import time
from types import SimpleNamespace as NS

import anthropic
import httpx2
import pytest

from behique.agent import Asker
from behique.config import Settings
from tests.test_api import _client, _wait


def _msg(content, stop="end_turn", **usage):
    u = NS(
        input_tokens=usage.get("input", 100),
        output_tokens=usage.get("output", 20),
        cache_read_input_tokens=usage.get("cache_read", 0),
        cache_creation_input_tokens=0,
        server_tool_use=NS(web_search_requests=usage.get("web", 0), web_fetch_requests=0),
    )
    return NS(
        content=content, stop_reason=stop, usage=u, model="claude-opus-5-5", stop_details=None
    )


def _text(t, citations=None):
    return NS(type="text", text=t, citations=citations)


class FakeClient:
    """Stands in for anthropic.Anthropic. ``script(tools)`` yields messages."""

    def __init__(self, script):
        self.script = script
        self.calls = []
        self.beta = NS(messages=NS(tool_runner=self._runner))

    def _runner(self, **kw):
        self.calls.append(kw)
        tools = {t.name if hasattr(t, "name") else t["name"]: t for t in kw["tools"]}
        return iter(list(self.script(tools)))


@pytest.fixture
def svc(tmp_path):
    c, svc, _ = _client(tmp_path)
    with c:
        c.post("/api/sources", json={"path": "notes"})
        c.post("/api/index")
        _wait(svc)
        yield c, svc


def _asker(svc, script, **settings):
    base = dict(
        data_root=svc.settings.data_root, db_path=svc.settings.db_path, anthropic_api_key="test"
    )
    return Asker(svc, Settings(**{**base, **settings}), client=FakeClient(script))


def test_local_answer_with_citation(svc):
    _, s = svc

    def script(tools):
        out = tools["search_local"].call({"query": "unique_token_xyz"})
        cid = int(out.split("[chunk:")[1].split("]")[0])
        assert "read_chunk" in tools and "web_search" not in tools
        assert tools["read_chunk"].call({"chunk_id": cid}).startswith(f"[chunk:{cid}]")
        yield _msg([NS(type="tool_use")], stop="tool_use")
        yield _msg([_text(f"It lives in a.md [chunk:{cid}]. Also [chunk:99999].")], cache_read=80)

    a = _asker(s, script)
    r = a.ask("where is unique_token_xyz?")
    assert r["citations"] == [r["citations"][0]] and r["citations"][0]["path"] == "a.md"
    assert r["usage"] == {
        "input": 200,
        "output": 40,
        "cache_read": 80,
        "cache_write": 0,
        "web_searches": 0,
        "web_fetches": 0,
        "steps": 2,
    }
    assert not r["step_cap_reached"] and not r["web_enabled"]

    kw = a.client.calls[0]
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kw["max_iterations"] == 6
    assert kw["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in kw["betas"]
    assert kw["output_config"] == {"effort": "low"}


def test_web_tools_only_when_allowed(svc):
    _, s = svc
    seen = {}

    def script(tools):
        seen["names"] = set(tools)
        cite = NS(url="https://example.com/x", title="X")
        yield _msg([_text("Current answer.", [cite])], web=1)

    r = _asker(s, script).ask("q", allow_web=True)  # setting off: request can't enable
    assert "web_search" not in seen["names"] and not r["web_enabled"]

    a = _asker(s, script, allow_web=True, web_allowed_domains=["example.com"])
    r = a.ask("q")
    assert {"web_search", "web_fetch"} <= seen["names"]
    assert r["citations"] == [{"type": "web", "url": "https://example.com/x", "title": "X"}]
    assert r["usage"]["web_searches"] == 1
    web = {t["name"]: t for t in a.client.calls[0]["tools"] if isinstance(t, dict)}
    assert web["web_fetch"]["max_content_tokens"] == 4000
    assert web["web_search"]["allowed_domains"] == ["example.com"]

    a.ask("q", allow_web=False)
    assert "web_search" not in seen["names"]


def test_step_cap_and_refusal(svc):
    _, s = svc
    r = _asker(s, lambda t: iter([_msg([_text("partial")], stop="tool_use")])).ask("q")
    assert r["step_cap_reached"] and r["answer"] == "partial"

    refusal = _msg([], stop="refusal")
    refusal.stop_details = NS(category="cyber")
    r = _asker(s, lambda t: iter([refusal])).ask("q")
    assert r["refused"] and r["refusal_category"] == "cyber" and r["answer"]


def test_haiku_has_no_fallback_and_task_budget(svc):
    _, s = svc
    a = _asker(
        s, lambda t: iter([_msg([_text("ok")])]), ask_model="claude-haiku-5-5", ask_task_budget=5000
    )
    a.ask("q")
    kw = a.client.calls[0]
    assert "fallbacks" not in kw
    assert kw["betas"] == ["task-budgets-2026-03-13"]
    assert kw["output_config"]["task_budget"] == {"type": "tokens", "total": 20000}


def test_source_filter_applies_to_tools(svc):
    _, s = svc

    def script(tools):
        assert tools["search_local"].call({"query": "unique_token_xyz"}) == "No results."
        yield _msg([_text("nothing")])

    _asker(s, script).ask("q", source_id=999)


def test_api_503_without_key(svc):
    c, _ = svc
    r = c.post("/api/ask", json={"question": "hi"})
    assert r.status_code == 503


def test_api_maps_upstream_errors(svc):
    c, s = svc
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    def boom(tools):
        raise anthropic.RateLimitError(
            "slow down",
            response=httpx2.Response(429, request=req, headers={"retry-after": "7"}),
            body=None,
        )
        yield  # pragma: no cover

    s._asker = _asker(s, boom)
    r = c.post("/api/ask", json={"question": "hi"})
    assert r.status_code == 429 and r.headers["retry-after"] == "7"

    def down(tools):
        raise anthropic.APIConnectionError(request=req)
        yield  # pragma: no cover

    s._asker = _asker(s, down)
    assert c.post("/api/ask", json={"question": "hi"}).status_code == 502


def _sse(text):
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_stream_emits_steps_answer_and_usage(svc):
    c, s = svc

    def script(tools):
        out = tools["search_local"].call({"query": "unique_token_xyz"})
        cid = int(out.split("[chunk:")[1].split("]")[0])
        tools["read_chunk"].call({"chunk_id": cid})
        yield _msg(
            [NS(type="server_tool_use", name="web_search", input={"query": "news"})],
            stop="tool_use",
        )
        yield _msg([_text(f"Found it [chunk:{cid}].")])

    s._asker = _asker(s, script)
    r = c.post("/api/ask/stream", json={"question": "where?"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = _sse(r.text)
    kinds = [e for e, _ in events]
    assert kinds == ["step", "step", "step", "delta", "citations", "usage", "done"]
    assert events[0][1] == {"kind": "search", "label": "Searching files: unique_token_xyz"}
    assert events[1][1]["label"] == "Reading a.md"
    assert events[2][1] == {"kind": "web_search", "label": "Searching the web: news"}
    assert events[3][1]["text"].startswith("Found it")
    assert events[4][1]["citations"][0]["path"] == "a.md"
    assert events[5][1]["steps"] == 2 and events[6][1]["refused"] is False


def test_stream_503_and_error_event(svc):
    c, s = svc
    assert c.post("/api/ask/stream", json={"question": "hi"}).status_code == 503
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    def down(tools):
        raise anthropic.APIConnectionError(request=req)
        yield  # pragma: no cover

    s._asker = _asker(s, down)
    events = _sse(c.post("/api/ask/stream", json={"question": "hi"}).text)
    assert events == [("error", {"status": 502, "detail": "could not reach the Claude API"})]


def test_closing_the_stream_stops_the_agent(svc):
    _, s = svc
    started, release = threading.Event(), threading.Event()
    calls = []

    def script(tools):
        def slow():
            tools["search_local"].call({"query": "a"})
            started.set()
            release.wait(5)
            calls.append(tools["search_local"].call({"query": "b"}))  # cancelled here
            yield _msg([_text("late")])

        return slow()

    a = _asker(s, script)
    a.client.beta.messages.tool_runner = lambda **kw: script(
        {t.name if hasattr(t, "name") else t["name"]: t for t in kw["tools"]}
    )
    gen = a.events("q")
    assert next(gen)[0] == "step"
    assert started.wait(5)
    gen.close()
    release.set()
    time.sleep(0.2)
    assert calls == []  # the second search raised instead of running
