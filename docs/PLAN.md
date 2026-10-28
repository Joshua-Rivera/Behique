# Behique: implementation plan (v1: core + REST API + MCP + agentic /ask + Docker)

## Context

A student project for learning RAG and building a portfolio piece, under tight time limits. It will be an open-source app that runs **locally in Docker**. It indexes folders the user explicitly mounts, using structure-aware chunking, tokenizer-aware sizing, local embeddings and a hybrid vector + BM25 store. It exposes the index through a **REST API** (the core interface), an **MCP endpoint** for agents such as Claude, and an opt-in **agentic RAG `/ask`** that searches local files first and goes to the web only when it must, to keep token use low. Hosting is out of scope, because indexing strangers' files on a server is a privacy and cost problem.

Agreed decisions from the design discussion:
- Approach 1: a local-first Python core with one service layer and thin clients on top (REST, MCP, `/ask`, and later the UI).
- Docker: the user mounts folders read-only (opt-in), the index lives in a named volume, the embedding model is baked into the image, and the image is multi-arch (amd64 and arm64).
- The API binds to 127.0.0.1 by default. If `API_KEY` is set, every request must send it.
- Change detection is a periodic rescan using content hash and mtime, not a file watcher (watchers are unreliable on Docker for Mac and Windows bind mounts).
- Retrieval runs vector search and BM25 (FTS5) and merges them with reciprocal rank fusion (RRF). A small committed eval set acts as the quality gate.
- `/ask` is enabled only when `ANTHROPIC_API_KEY` is set. Web access also needs `ALLOW_WEB=true`. Without the key, the container stays fully offline.
- **Out of v1:** the Apple-style UI (Next.js + shadcn/ui, per `Research/07UIRESEARCH.md`), a reranker and a desktop wrapper. These come later, as separate specs.

## Repository and git workflow

- **Repo:** https://github.com/Joshua-Rivera/Behique (public, default branch `main`). It currently has `README.md` and `Research/00–09*.md`. Keep `Research/` untouched, because it's the owner's study notes.
- **Local clone:** `~/Desktop/Desktop/Behique`. The Claude Code session moves there before any edit.
- **Authorship: no co-authoring.** Commits are authored only by the repo owner's git identity (Joshua Rivera). Commits get no `Co-Authored-By` trailers, and PR descriptions get no "Generated with Claude Code" lines. This user instruction overrides any default attribution.
- **Branching (GitHub flow):**
  - `main` is always releasable and protected.
  - Each milestone gets its own branch off `main`: `feat/<milestone>-<topic>`, for example `feat/m1-store`, `feat/m2-chunking`, `feat/m7b-agentic-ask`. Fixes use `fix/<topic>`, CI changes `ci/<topic>`, docs `docs/<topic>`.
  - One PR per branch, merged by squash after CI passes. Delete the branch after merge.
  - Conventional Commit messages (`feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`).
- **Branch protection on `main`** (the owner sets this in GitHub settings, since it changes the account's repo config): require a PR, require the `ci` status checks to pass, and block force-pushes.
- **Releases:** SemVer tags `v0.1.0`, and so on. A tag triggers CD.

## CI/CD (`.github/workflows/`)

| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | Pull request to `main`, push to `main` | **lint** (`ruff check`, `ruff format --check`); **test** (`uv sync`, `pytest` with coverage, mocked Anthropic client, no paid calls); **eval** (`make eval`, which fails if hybrid hit@5 drops below the committed baseline in `eval/baseline.json`); **docker** (buildx build for amd64 + arm64, no push, then a container smoke test of `/health`). |
| `release.yml` | Push of tag `v*` | Builds and pushes the multi-arch image to `ghcr.io/joshua-rivera/behique:{version,latest}` with `GITHUB_TOKEN`, then creates a GitHub Release with auto-generated notes. |
| `codeql.yml` | Weekly, and PRs to `main` | GitHub CodeQL for Python. |
| `.github/dependabot.yml` | Weekly | Updates `pip`/`uv`, GitHub Actions and Docker base images. |

Also add `.github/pull_request_template.md` (what changed, how it was tested, eval delta), `CONTRIBUTING.md` (the branch, commit and PR rules above) and `LICENSE` (MIT).

## Which model implements each feature

These are the models for **building** the app in Claude Code (switch with `/model` per branch). The runtime model used by `/ask` is a separate, configurable setting (see "Agentic /ask").

| Milestone / feature | Implementer model | Effort | Why |
|---|---|---|---|
| M0: Spec doc, repo setup, CONTRIBUTING, PR template | `claude-sonnet-5-5` | medium | Mostly structure and text. |
| M1: SQLite schema, `sqlite-vec` + FTS5 sync triggers, migrations | `claude-opus-5-5` | high | Data model mistakes are expensive to undo. |
| M1: `tokens.py`, `embed.py` wrappers | `claude-sonnet-5-5` | medium | Thin library wrappers. |
| M2: Extractors (md, txt, code, pdf, docx) | `claude-sonnet-5-5` | medium | Straightforward, pattern-based. |
| M2: Chunkers + token packing with overlap and offset mapping | `claude-opus-5-5` | high | Subtle edge cases (tree-sitter symbols, offsets, hard token cap). This is the core of retrieval quality. |
| M3: Scanner, deny-list, hash diff, indexer job and lock | `claude-sonnet-5-5` | high | Moderate logic, with tests to verify it. |
| M4: Hybrid search + RRF + filters | `claude-opus-5-5` | high | Ranking logic, which the eval gate measures. |
| M5: Eval corpus, questions, `run.py`, baseline | `claude-sonnet-5-5` | medium | Needs care with question correctness but no deep reasoning. |
| M6: REST API, service layer, API-key auth, rescan task | `claude-sonnet-5-5` | medium | Standard FastAPI. |
| M7: MCP server | `claude-sonnet-5-5` | medium | A thin wrapper over the service layer. |
| M7b: Agentic `/ask` (`agent.py`, tool loop, web tools, budgets, caching) | `claude-opus-5-5` | high | Agent design, token economics and prompt-injection safety. |
| M8: Dockerfile, compose, CI/CD workflows, Dependabot, CodeQL | `claude-sonnet-5-5` | medium | Well-known patterns. |
| M9: README, diagrams, demo script | `claude-haiku-5-5` | medium | Prose and formatting from finished facts. Review afterwards. |
| Small chores (lint fixes, renames, commit messages, PR descriptions) | `claude-haiku-5-5` | low | Cheap and fast. |
| **Review before each merge** (`/code-review` on the PR) | `claude-opus-5-5` | high | A second pass on correctness and security for every milestone. |

## Stack

Python 3.12, `uv`, FastAPI and Pydantic, `sqlite3` + `sqlite-vec` + FTS5, `fastembed` (`BAAI/bge-small-en-v1.5`: 384 dimensions, 512-token limit), `tokenizers` (that model's own tokenizer), `tree-sitter-language-pack`, `pypdf`, `python-docx`, the `mcp` Python SDK (FastMCP over streamable HTTP, mounted in the same FastAPI app), the `anthropic` Python SDK (for `/ask`), `pytest`, `ruff`. Before writing `agent.py`, read the claude-api skill's `python/claude-api/README.md` and `tool-use.md`. No LangChain or LlamaIndex: the pipeline is hand-written so it can be explained in interviews.

## Project layout (added to the existing repo)

```
Behique/
  README.md  CONTRIBUTING.md  LICENSE  pyproject.toml  Makefile  Dockerfile  docker-compose.yml
  Research/                       # existing notes, untouched
  docs/PLAN.md                    # this plan
  docs/superpowers/specs/2026-10-28-behique-design.md
  .github/workflows/{ci,release,codeql}.yml  .github/dependabot.yml  .github/pull_request_template.md
  src/behique/
    config.py        # settings from env: DATA_ROOT=/data, DB_PATH, API_KEY, CHUNK_TOKENS=400, OVERLAP=0.15,
                     #   RESCAN_SECONDS, size cap, ANTHROPIC_API_KEY, ASK_MODEL, ASK_EFFORT, ASK_MAX_STEPS,
                     #   ALLOW_WEB, WEB_ALLOWED_DOMAINS / WEB_BLOCKED_DOMAINS
    store.py         # schema, migrations, upserts/deletes, vec + fts queries
    scan.py          # walk DATA_ROOT, deny-list, size cap, binary detection, hash/mtime diff
    extract/         # registry: ext -> extractor; text.py (md/txt/code), pdf.py, docx.py
    chunk/           # markdown.py, code.py (tree-sitter), prose.py, pack.py (token packing + overlap)
    tokens.py        # count(text) using the embedding model's tokenizer
    embed.py         # fastembed wrapper, batched; exposes model name + dim
    indexer.py       # pipeline orchestration, background job, single-flight lock, status
    search.py        # vector_search, bm25_search, rrf_merge, metadata filters
    service.py       # THE service layer: sources, index, status, search, read_file, ask
    agent.py         # agentic /ask: Claude tool loop, budgets, usage reporting
    api.py           # FastAPI routes + API-key dependency
    mcp_server.py    # FastMCP tools wrapping service.py
    main.py          # app factory, mounts MCP at /mcp, starts periodic rescan
  tests/
  eval/
    corpus/  questions.jsonl  baseline.json
    run.py           # hit@k + MRR for vector / bm25 / hybrid
    ask_eval.py      # about 10 questions: answer correctness, citation, tokens per question (manual, real key)
```

## Data model (SQLite, one file in the volume)

- `meta(key, value)`: stores the embedding model name, its dimension and the schema version. If the model changes, the whole index is rebuilt.
- `sources(id, name, path UNIQUE, created_at)`. The path must resolve under `DATA_ROOT`.
- `files(id, source_id, rel_path, size, mtime, content_hash, status[indexed|skipped|error], error, indexed_at)`
- `chunks(id, file_id, ordinal, text, start_char, end_char, token_count, heading_path, symbol)`
- `chunks_fts`: an FTS5 table over `chunks.text` (external content, kept in sync by triggers).
- `chunks_vec`: a `vec0` table with `embedding float[384]`, keyed by chunk id.

A re-indexed file deletes its old chunks, fts rows and vec rows in one transaction, then inserts the new ones.

## Service API

| Endpoint | Behavior |
|---|---|
| `GET /health` | `{ok, model, chunks}` |
| `POST /sources` `{name, path}` | Register a mounted folder. 400 if the path is outside `DATA_ROOT` or missing. |
| `GET /sources` | List sources with file and chunk counts and the last indexed time. |
| `POST /index` `{source_id?}` | Start a background index run. Returns 409 if one is already running. |
| `GET /index/status` | Running flag, files seen, changed, failed, chunks embedded, recent errors. |
| `POST /search` `{query, k=8, mode=hybrid\|vector\|bm25, source_id?, ext?, path_prefix?}` | Ranked chunks: path, offsets, heading_path or symbol, score, the retrievers that found it, and text. |
| `GET /files/{file_id}?chunk_id=&context=` | File text, or a chunk with N surrounding chunks. Looked up only by id, never by a user-supplied path. |
| `POST /ask` `{question, allow_web?, source_id?}` | Runs the agentic loop. Returns `{answer, citations[local \| web], usage{input, output, cache_read, web_searches, steps}}`. Returns 503 when no API key is configured. |

MCP tools (at `/mcp`): `search_files`, `read_file`, `list_sources`. MCP doesn't expose `ask`, because the MCP client is already an LLM.

## Agentic /ask (agent.py)

- **Loop.** It uses the Anthropic SDK Tool Runner (`client.beta.messages.tool_runner` with `@beta_tool`). If server-tool `pause_turn` handling doesn't fit the runner, it falls back to a manual loop. It has a hard cap of `ASK_MAX_STEPS=6` and returns its best answer plus a flag when it hits the cap.
- **Tools.**
  - `search_local(query, k=5, filters)` returns compact hits with snippets of at most about 400 characters.
  - `read_chunk(chunk_id, context=1)` expands one hit on demand.
  - `web_search` (`web_search_20260209`, `max_uses=3`) and `web_fetch` (`web_fetch_20260209`, `max_uses=2`, `max_content_tokens=4000`) are included only when web access is allowed. Both have built-in dynamic filtering.
- **Runtime model.** `ASK_MODEL` defaults to `claude-opus-5-5` with `ASK_EFFORT=low`. You can set `ASK_MODEL=claude-haiku-5-5` for the cheapest runs. `ask_eval.py` measures the quality and cost difference so you can choose with numbers.
- **Token minimization.**
  1. Search local first, and send snippets before full text. The model never receives whole files.
  2. The system prompt says to use the web only for missing or current facts, stop once the question is answered, and give concise answers with citations.
  3. Prompt caching: the tools and system prompt are frozen and deterministic, with a `cache_control` breakpoint after the system prompt. Verify `cache_read_input_tokens > 0`.
  4. Budgets: the step cap, the web `max_uses` limits, `max_content_tokens`, and an optional `task_budget` (beta `task-budgets-2026-03-13`, minimum 20k).
  5. `usage` is reported on every response, and the eval logs tokens per question. That gives the README a measured claim.
  - Stretch goal: cache fetched web pages into a `web` source in the local index.
- **Safety.**
  - Chunks and the question go to Anthropic only when `/ask` is used, and the README says so.
  - File and web content goes into tool results only, never into the system prompt.
  - All of the agent's tools are read-only.
  - `web_fetch` only fetches URLs already in the conversation. Optional domain allow and block lists narrow it further.
  - Residual risk (documented): an injected document could try to exfiltrate file content through a web query. Mitigations are web access off by default plus the domain lists.
  - Handle `stop_reason == "refusal"` and enable server-side fallbacks (beta `server-side-fallback-2026-07-01`, `fallbacks: "default"`). API errors map to 502, or to 429 with retry-after.

## Build order (one branch and PR per milestone, about 14 h total)

Each milestone ends with tests passing, a squash-merged PR and green CI on `main`.

1. **M0 `feat/m0-setup` (0.5 h).** Clone the repo. Add `uv init` and `src/behique` layout, ruff, pytest, the Makefile (`test`, `eval`, `run`, `docker`), the spec doc, `docs/PLAN.md`, CONTRIBUTING, the PR template, LICENSE, and a minimal `ci.yml` (lint + test) so every later PR is gated from day one.
2. **M1 `feat/m1-store` (1.5 h).** `tokens.py`, `embed.py`, `store.py` and a round-trip test (insert, then a vec query and an fts query).
3. **M2 `feat/m2-chunking` (2 h).** Extractors and chunkers. Tests: no chunk exceeds 512 tokens, overlap is applied, heading_path and symbol are filled in, and offsets map back to the source text.
4. **M3 `feat/m3-indexer` (1.5 h).** Scan, deny-list, incremental diff, deletions, per-file errors and the lock. Tests modify a temp folder between runs.
5. **M4 `feat/m4-search` (1 h).** Vector, BM25 and RRF search with filters. Tests: an exact identifier is found by BM25, and a paraphrase is found by vector search.
6. **M5 `feat/m5-eval` (1 h).** Corpus, questions, `run.py` and `baseline.json`. Add the `eval` job to `ci.yml`.
7. **M6 `feat/m6-api` (1 h).** Service layer, routes, API-key auth and periodic rescan. TestClient tests.
8. **M7 `feat/m7-mcp` (0.5–1 h).** `mcp_server.py` mounted at `/mcp`.
9. **M7b `feat/m7b-agentic-ask` (2 h).** `agent.py`, `/ask` and the env flags. Mocked tests: step cap, citation mapping, web tools absent when disabled, 503 with no key. Run `ask_eval.py` manually.
10. **M8 `ci/m8-docker-cicd` (1.5 h).** Dockerfile (multi-stage, model baked in, non-root, HEALTHCHECK), compose file, the full `ci.yml` docker job, `release.yml`, `codeql.yml` and `dependabot.yml`.
11. **M9 `docs/m9-readme` (1 h).** Quickstart, MCP setup, architecture diagram, the eval and token tables, privacy notes and a demo GIF. Then tag `v0.1.0`, which triggers the release workflow.

## Error handling

- Per-file failures are stored in `files.error` and indexing continues. Unsupported, binary and oversized files are marked `skipped` with a reason.
- A second index request while one is running returns 409. Rescans skip their turn if a job is running.
- An embedding model mismatch with `meta` triggers a full rebuild and a warning.
- Source paths are checked against `DATA_ROOT`. `/files` takes ids only.
- When `API_KEY` is set, requests without it get 401. The compose file binds to localhost only.

## Verification

- `make test` and `make eval` pass locally. Hybrid scores at least as well as each single mode.
- `docker compose up --build`, then curl `/health`, `/sources`, `/index`, `/index/status` and `/search`, and check that the results come back with citations.
- Privacy: a fake `.env` in a mounted folder never shows up in search, and writing to `/data` inside the container fails.
- Incremental: edit one file, rescan, and `/index/status` shows 1 changed file.
- MCP: `claude mcp add --transport http behique http://localhost:8000/mcp`. Claude answers a question using `search_files` and cites a real file.
- `/ask`:
  - With no key it returns 503.
  - Local-only mode answers with a local citation and no web usage.
  - Web mode cites a URL for a question about a current fact.
  - A repeated call shows cache reads.
- GitHub: every milestone PR shows green `ci` checks. `git log` shows no `Co-Authored-By` trailers. Pushing tag `v0.1.0` publishes `ghcr.io/joshua-rivera/behique` for both architectures and creates a release.
