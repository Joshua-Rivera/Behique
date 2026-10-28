# Behique design spec (v1)

Behique is a local-first RAG service: a Python core with one service layer and thin
clients (REST, MCP, agentic `/ask`) on top. It indexes only folders the user mounts
read-only into Docker, using structure-aware chunking, tokenizer-aware sizing, local
embeddings (`BAAI/bge-small-en-v1.5`) and a hybrid sqlite-vec + FTS5 store merged with RRF.

The full design, data model, API, build order and CI/CD are in [`../../PLAN.md`](../../PLAN.md),
which is the binding reference for v1. Out of scope for v1: the UI, a reranker, a desktop wrapper.
