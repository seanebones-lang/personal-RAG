"""Export controls for query turns."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from src.export import export_turn_json, export_turn_markdown


def render_export_buttons(
    question: str,
    answer: Optional[str],
    results: List[Dict[str, Any]],
) -> None:
    if not results:
        return
    st.download_button(
        "Export JSON",
        export_turn_json(question, answer, results),
        file_name="query_results.json",
        mime="application/json",
    )
    st.download_button(
        "Export Markdown",
        export_turn_markdown(question, answer, results),
        file_name="query_results.md",
        mime="text/markdown",
    )
