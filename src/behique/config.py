"""Settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    data_root: Path = field(default_factory=lambda: Path(os.environ.get("DATA_ROOT", "/data")))
    db_path: Path = field(
        default_factory=lambda: Path(os.environ.get("DB_PATH", "/index/behique.db"))
    )
    model_cache: str | None = field(default_factory=lambda: os.environ.get("MODEL_CACHE") or None)
    api_key: str | None = field(default_factory=lambda: os.environ.get("API_KEY") or None)
    chunk_tokens: int = field(default_factory=lambda: int(os.environ.get("CHUNK_TOKENS", "400")))
    overlap: float = field(default_factory=lambda: float(os.environ.get("OVERLAP", "0.15")))
    rescan_seconds: int = field(
        default_factory=lambda: int(os.environ.get("RESCAN_SECONDS", "300"))
    )
    max_file_bytes: int = field(
        default_factory=lambda: int(os.environ.get("MAX_FILE_BYTES", str(10 * 1024 * 1024)))
    )
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY") or None
    )
    ask_model: str = field(default_factory=lambda: os.environ.get("ASK_MODEL", "claude-opus-5-5"))
    ask_effort: str = field(default_factory=lambda: os.environ.get("ASK_EFFORT", "low"))
    ask_max_steps: int = field(default_factory=lambda: int(os.environ.get("ASK_MAX_STEPS", "6")))
    ask_task_budget: int | None = field(
        default_factory=lambda: (
            int(os.environ["ASK_TASK_BUDGET"]) if os.environ.get("ASK_TASK_BUDGET") else None
        )
    )
    ask_demo: bool = field(default_factory=lambda: _bool("ASK_DEMO"))
    allow_web: bool = field(default_factory=lambda: _bool("ALLOW_WEB"))
    web_allowed_domains: list[str] = field(default_factory=lambda: _list("WEB_ALLOWED_DOMAINS"))
    web_blocked_domains: list[str] = field(default_factory=lambda: _list("WEB_BLOCKED_DOMAINS"))
    web_dir: Path = field(default_factory=lambda: Path(os.environ.get("WEB_DIR", "/app/web")))
    dev_cors: bool = field(default_factory=lambda: _bool("DEV_CORS"))
