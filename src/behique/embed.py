"""Local embeddings with fastembed (BAAI/bge-small-en-v1.5)."""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIM = 384
MAX_TOKENS = 512
# bge recommends this prefix on queries (not passages) for retrieval.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def get_model(cache_dir: str | None = None) -> TextEmbedding:
    # MODEL_CACHE lets the Docker image ship the model and run offline.
    return _load(cache_dir or os.environ.get("MODEL_CACHE") or None)


@lru_cache(maxsize=4)
def _load(cache_dir: str | None) -> TextEmbedding:
    return TextEmbedding(MODEL_NAME, cache_dir=cache_dir)


def model_dir(cache_dir: str | None = None) -> Path:
    return Path(get_model(cache_dir).model._model_dir)


class Embedder:
    def __init__(self, cache_dir: str | None = None, batch_size: int = 64) -> None:
        self._model = get_model(cache_dir)
        self.batch_size = batch_size
        self.name = MODEL_NAME
        self.dim = DIM

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return self._run(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._run([QUERY_PREFIX + text])[0]

    def _run(self, texts: Iterable[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.embed(list(texts), batch_size=self.batch_size)]
