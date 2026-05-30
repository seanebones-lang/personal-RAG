"""Result card rendering."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import streamlit as st


def render_results(
    results: List[Dict[str, Any]],
    on_select: Callable[[str, str], None],
) -> Optional[str]:
    """Render expandable result cards; return selected source path."""
    selected: Optional[str] = None
    for i, row in enumerate(results, 1):
        meta = row.get("metadata") or {}
        source = str(meta.get("source", meta.get("file_name", "?")))
        score = row.get("rerank_score")
        if score is None:
            score = row.get("rrf_score")
        dist = row.get("distance", 0)
        if score is not None:
            score_label = f"score {float(score):.4f}"
        else:
            score_label = f"dist {dist:.4f}"
        year = meta.get("year", "")
        ext = meta.get("extension", "")
        title = f"{i}. {source} — {score_label}"
        with st.expander(title, expanded=i == 1):
            st.caption(f"year={year} ext={ext}")
            text = row.get("text", "")
            st.text(text[:2000])
            if st.button("Preview source", key=f"preview_{i}"):
                on_select(source, text[:500])
                selected = source
    return selected
