"""Manual /ask eval: answer correctness, citation and tokens per question.

Spends real tokens. Run with a key, optionally comparing models:

    ANTHROPIC_API_KEY=... uv run python eval/ask_eval.py
    ANTHROPIC_API_KEY=... ASK_MODEL=claude-haiku-5-5 uv run python eval/ask_eval.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from behique.config import Settings
from behique.embed import Embedder
from behique.service import Service
from behique.store import Store

HERE = Path(__file__).parent

# (question, substrings any of which must appear in the answer, expected cited file)
CASES = [
    ("How often should I feed my sourdough starter?", ["twice"], "notes/sourdough.md"),
    ("What oven temperature do I bake the bread at?", ["250"], "notes/sourdough.md"),
    (
        "How long is the train from Lisbon to Porto?",
        ["three hours", "3 hours"],
        "notes/portugal-trip.md",
    ),
    ("What did the Portugal trip cost in total?", ["1,400", "1400"], "notes/portugal-trip.md"),
    ("Who owns the job queue migration?", ["Marco"], "notes/meeting-2026-09-14.md"),
    (
        "What does TokenBucket.allow return when there aren't enough tokens?",
        ["False"],
        "code/ratelimit.py",
    ),
    (
        "What jitter strategy does retry_with_backoff use?",
        ["full jitter", "uniform"],
        "code/retry.py",
    ),
    ("Which UDP port does the office VPN use?", ["51820"], "docs/vpn-setup.txt"),
    ("What is the daily meal allowance when travelling?", ["60"], "docs/expense-policy.txt"),
    ("When do the Perseids peak?", ["12 August", "August 12"], "docs/astronomy.md"),
]


def main() -> int:
    emb = Embedder()
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_root=HERE, db_path=Path(tmp) / "a.db")
        if not settings.anthropic_api_key:
            print("set ANTHROPIC_API_KEY to run this eval", file=sys.stderr)
            return 2
        svc = Service(settings, Store(settings.db_path, emb.name, emb.dim), emb)
        svc.add_source("corpus", "corpus")
        svc.indexer.run()
        rows, correct, cited = [], 0, 0
        for q, needles, path in CASES:
            r = svc.ask(q, allow_web=False)
            ok = any(n.lower() in r["answer"].lower() for n in needles)
            cit = any(c.get("path") == path for c in r["citations"])
            correct += ok
            cited += cit
            u = r["usage"]
            rows.append({"q": q, "correct": ok, "cited": cit, **u})
            print(
                f"{'✓' if ok else '✗'}{'c' if cit else ' '} in={u['input']:>6} "
                f"out={u['output']:>5} cache={u['cache_read']:>6} steps={u['steps']}  {q}"
            )
        n = len(CASES)
        tot_in = sum(r["input"] for r in rows)
        tot_out = sum(r["output"] for r in rows)
        print(f"\nmodel={settings.ask_model} effort={settings.ask_effort}")
        print(
            f"correct {correct}/{n}  cited {cited}/{n}  "
            f"avg input {tot_in / n:.0f}  avg output {tot_out / n:.0f} tokens/question"
        )
        (HERE / "ask_results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
