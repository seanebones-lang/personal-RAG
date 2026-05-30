"""Export query turns to Markdown or JSON."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _serialize_result(row: Dict[str, Any]) -> Dict[str, Any]:
    meta = row.get("metadata") or {}
    return {
        "source": meta.get("source", meta.get("file_name")),
        "score": row.get("rerank_score") or row.get("rrf_score") or row.get("distance"),
        "text": row.get("text", ""),
        "metadata": dict(meta),
    }


def export_turn_json(
    question: str,
    answer: Optional[str],
    results: List[Dict[str, Any]],
) -> str:
    payload = {
        "question": question,
        "answer": answer,
        "results": [_serialize_result(r) for r in results],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_turn_markdown(
    question: str,
    answer: Optional[str],
    results: List[Dict[str, Any]],
) -> str:
    lines = [f"# Query\n\n{question}\n"]
    if answer:
        lines.append(f"## Answer\n\n{answer}\n")
    lines.append("## Retrieved chunks\n")
    for i, row in enumerate(results, 1):
        meta = row.get("metadata") or {}
        source = meta.get("source", meta.get("file_name", "?"))
        score = row.get("rerank_score") or row.get("rrf_score") or row.get("distance")
        lines.append(f"### {i}. {source}\n")
        if score is not None:
            lines.append(f"_score: {score}_\n\n")
        lines.append(f"{row.get('text', '')}\n")
    return "\n".join(lines)
