"""Conversation session state."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_source" not in st.session_state:
        st.session_state.selected_source = None


def add_turn(question: str, answer: str | None, results: List[Dict[str, Any]]) -> None:
    st.session_state.messages.append(
        {
            "question": question,
            "answer": answer,
            "result_count": len(results),
            "top_source": (results[0].get("metadata") or {}).get("source") if results else None,
        }
    )


def render_history_sidebar() -> None:
    st.sidebar.subheader("History")
    if not st.session_state.messages:
        st.sidebar.caption("No queries yet.")
        return
    for i, msg in enumerate(reversed(st.session_state.messages), 1):
        st.sidebar.markdown(f"**{i}.** {msg['question'][:60]}")
        if msg.get("answer"):
            st.sidebar.caption(msg["answer"][:80])
