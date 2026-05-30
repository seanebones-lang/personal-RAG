"""Load evaluation datasets from JSONL."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class EvalCase:
    question: str
    expected_source_contains: str
    optional_year: Optional[int] = None


def load_dataset(path: Path) -> List[EvalCase]:
    cases: List[EvalCase] = []
    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
        if "question" not in row or "expected_source_contains" not in row:
            raise ValueError(
                f"Line {line_no} must include 'question' and 'expected_source_contains'"
            )
        year = row.get("optional_year")
        cases.append(
            EvalCase(
                question=str(row["question"]),
                expected_source_contains=str(row["expected_source_contains"]),
                optional_year=int(year) if year is not None else None,
            )
        )
    return cases
