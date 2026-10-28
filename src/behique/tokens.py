"""Token counting with the embedding model's own tokenizer."""

from __future__ import annotations

from functools import lru_cache

from tokenizers import Tokenizer

from behique.embed import model_dir


@lru_cache(maxsize=4)
def get_tokenizer(cache_dir: str | None = None) -> Tokenizer:
    tok = Tokenizer.from_file(str(model_dir(cache_dir) / "tokenizer.json"))
    tok.no_truncation()
    tok.no_padding()
    return tok


def count(text: str, cache_dir: str | None = None) -> int:
    """Number of tokens excluding the [CLS]/[SEP] specials."""
    return len(get_tokenizer(cache_dir).encode(text, add_special_tokens=False).ids)


def offsets(text: str, cache_dir: str | None = None) -> list[tuple[int, int]]:
    """Character span of every token in ``text``."""
    return get_tokenizer(cache_dir).encode(text, add_special_tokens=False).offsets
