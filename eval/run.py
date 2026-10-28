"""Retrieval eval: hit@k and MRR per mode over a small committed corpus.

uv run python eval/run.py              # print the table
uv run python eval/run.py --check      # fail if hybrid hit@5 drops below baseline
uv run python eval/run.py --write-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from behique.config import Settings
from behique.embed import Embedder
from behique.indexer import Indexer
from behique.search import search
from behique.store import Store

HERE = Path(__file__).parent
MODES = ("vector", "bm25", "hybrid")
K = 5


def evaluate() -> dict:
    questions = [json.loads(line) for line in (HERE / "questions.jsonl").read_text().splitlines()]
    emb = Embedder()
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "eval.db", emb.name, emb.dim)
        store.add_source("corpus", str((HERE / "corpus").resolve()))
        Indexer(store, emb, Settings(data_root=HERE, db_path=Path(tmp) / "eval.db")).run()
        results = {}
        for mode in MODES:
            hits, rr = 0, 0.0
            for item in questions:
                paths = []
                for h in search(store, emb, item["q"], k=K * 3, mode=mode):
                    if h.path not in paths:
                        paths.append(h.path)
                paths = paths[:K]
                if item["expected"] in paths:
                    hits += 1
                    rr += 1.0 / (paths.index(item["expected"]) + 1)
            n = len(questions)
            results[mode] = {f"hit@{K}": round(hits / n, 4), "mrr": round(rr / n, 4)}
        store.close()
    return {"questions": len(questions), "k": K, "modes": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()

    res = evaluate()
    print(f"{'mode':<8} {'hit@' + str(K):>7} {'MRR':>7}   ({res['questions']} questions)")
    for mode, m in res["modes"].items():
        print(f"{mode:<8} {m[f'hit@{K}']:>7.3f} {m['mrr']:>7.3f}")

    base_path = HERE / "baseline.json"
    if args.write_baseline:
        base_path.write_text(json.dumps(res, indent=2) + "\n")
        print(f"wrote {base_path}")
    if args.check:
        base = json.loads(base_path.read_text())
        key = f"hit@{K}"
        got, want = res["modes"]["hybrid"][key], base["modes"]["hybrid"][key]
        if got < want:
            print(f"FAIL: hybrid {key} {got} < baseline {want}", file=sys.stderr)
            return 1
        print(f"OK: hybrid {key} {got} >= baseline {want}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
