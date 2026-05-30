"""Safe document preview for UI."""

from __future__ import annotations

import streamlit as st

from src.core.vault import preview_source


def render_preview_panel(selected_source: str | None) -> None:
    st.subheader("Document preview")
    if not selected_source:
        st.caption("Select a result to preview its source file.")
        return
    st.text(selected_source)
    content = preview_source(selected_source)
    st.text_area("Content", content, height=300)
