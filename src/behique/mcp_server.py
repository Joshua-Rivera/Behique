"""MCP tools over streamable HTTP, mounted at /mcp. Thin wrappers over ``Service``.

``ask`` is deliberately not exposed: the MCP client is already an LLM.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from behique.service import Service

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
SNIPPET = 1200


def build_mcp(get_service: Callable[[], Service]) -> MCPServer:
    mcp = MCPServer(
        "behique",
        instructions=(
            "Search the user's locally indexed files. Call search_files first, then "
            "read_file with a hit's file_id and chunk_id for more context. Cite paths."
        ),
    )

    @mcp.tool(annotations=READ_ONLY)
    def search_files(
        query: str,
        k: int = 8,
        mode: Literal["hybrid", "vector", "bm25"] = "hybrid",
        source_id: int | None = None,
        ext: str | None = None,
        path_prefix: str | None = None,
    ) -> list[dict]:
        """Search indexed files. Hybrid (semantic + keyword) by default.

        Use bm25 for exact identifiers. Returns ranked chunks with path, heading or
        symbol, file_id and chunk_id.
        """
        hits = get_service().search(query, k, mode, source_id, ext, path_prefix)
        for h in hits:
            if len(h["text"]) > SNIPPET:
                h["text"] = h["text"][:SNIPPET] + " …"
        return hits

    @mcp.tool(annotations=READ_ONLY)
    def read_file(file_id: int, chunk_id: int | None = None, context: int = 1) -> dict:
        """Read an indexed file by id, or one chunk plus ``context`` neighbouring chunks."""
        return get_service().read_file(file_id, chunk_id, context)

    @mcp.tool(annotations=READ_ONLY)
    def list_sources() -> list[dict]:
        """List indexed folders with file and chunk counts."""
        return get_service().list_sources()

    return mcp
