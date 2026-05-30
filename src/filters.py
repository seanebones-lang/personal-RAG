"""Build Chroma metadata filters from CLI options."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def build_where(
    where_year: Optional[int] = None,
    source_contains: Optional[str] = None,
    extension: Optional[str] = None,
    filter_json: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Merge CLI filter options into a Chroma where clause."""
    clauses: list[Dict[str, Any]] = []

    if where_year is not None:
        clauses.append({"year": where_year})
    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        clauses.append({"extension": ext})
    if source_contains:
        clauses.append({"source": {"$contains": source_contains}})

    if filter_json:
        try:
            custom = json.loads(filter_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid --filter JSON: {exc}") from exc
        if not isinstance(custom, dict):
            raise ValueError("--filter must be a JSON object")
        clauses.append(custom)

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
