"""Safe document preview for UI."""

from __future__ import annotations

import streamlit as st

from src.core.vault import highlight_excerpt, preview_source


def render_preview_panel(
    selected_source: str | None,
    excerpt: str | None = None,
) -> None:
    st.subheader("Document preview")
    if not selected_source:
        st.caption("Select a result to preview its source file.")
        return
    st.text(selected_source)
    content = preview_source(selected_source)
    if excerpt:
        content = highlight_excerpt(content, excerpt)
        st.markdown(content[:8000])
    else:
        st.text_area("Content", content, height=300)
