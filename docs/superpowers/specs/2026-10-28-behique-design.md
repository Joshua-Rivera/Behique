# Behique design (v1)

Status: agreed, 2026-10-28. Full implementation plan: [`docs/PLAN.md`](../../PLAN.md).

## Goal

A local-first, open-source RAG app that runs in Docker, indexes only folders the user mounts
read-only, and exposes that index through a REST API, an MCP endpoint and an opt-in agentic `/ask`.

## Architecture

One Python core with a single service layer (`service.py`); REST, MCP and `/ask` are thin clients.

```
mounted folders (ro) → scan → extract → chunk (structure + token aware) → embed (bge-small, 384d)
                                                      ↓
                                SQLite: chunks + FTS5 (BM25) + sqlite-vec
                                                      ↓
                          search: vector + BM25 → RRF  →  service.py
                                                      ↓
                              REST API  ·  MCP (/mcp)  ·  /ask (Claude tool loop)
```

## Key decisions

- Folders are opt-in, mounted read-only; the index lives in a named volume; the model is baked in.
- API binds to 127.0.0.1; optional `API_KEY` required on every request.
- Change detection by periodic rescan (content hash + mtime), not file watchers.
- Hybrid retrieval with reciprocal rank fusion, gated in CI by a committed eval baseline.
- `/ask` only with `ANTHROPIC_API_KEY`; web tools only with `ALLOW_WEB=true`. Otherwise fully offline.
- No LangChain/LlamaIndex: the pipeline is hand-written to be explainable.

## Out of scope for v1

Web UI, reranker, desktop wrapper, hosting.
