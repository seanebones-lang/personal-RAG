"""Run evaluation over a JSONL dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.vault import run_query
from src.eval.dataset import load_dataset
from src.eval.metrics import EvalResult, aggregate, score_retrieval
from src.filters import build_where


def run_evaluation(
    dataset_path: Path,
    top_k: int = 5,
    hybrid: bool = False,
    output_json: Optional[Path] = None,
) -> Dict[str, Any]:
    cases = load_dataset(dataset_path)
    results: List[EvalResult] = []

    for case in cases:
        where = None
        if case.optional_year is not None:
            where = build_where(where_year=case.optional_year)

        out = run_query(
            case.question,
            top_k=top_k,
            where=where,
            hybrid=hybrid,
            use_llm=False,
        )
        hit, rr = score_retrieval(
            out["results"],
            case.expected_source_contains,
            top_k,
        )
        results.append(
            EvalResult(
                question=case.question,
                hit=hit,
                reciprocal_rank=rr,
                expected=case.expected_source_contains,
            )
        )

    summary = aggregate(results)
    payload = {
        "summary": summary,
        "cases": [
            {
                "question": r.question,
                "expected": r.expected,
                "hit": r.hit,
                "reciprocal_rank": r.reciprocal_rank,
            }
            for r in results
        ],
    }
    if output_json:
        output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
