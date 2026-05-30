"""Conversation session state."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_source" not in st.session_state:
        st.session_state.selected_source = None
    if "selected_excerpt" not in st.session_state:
        st.session_state.selected_excerpt = None
    if "active_turn" not in st.session_state:
        st.session_state.active_turn = None


def add_turn(
    question: str,
    answer: str | None,
    results: List[Dict[str, Any]],
) -> None:
    turn = {
        "question": question,
        "answer": answer,
        "results": results,
        "result_count": len(results),
        "top_source": (results[0].get("metadata") or {}).get("source") if results else None,
    }
    st.session_state.messages.append(turn)
    st.session_state.active_turn = len(st.session_state.messages) - 1


def clear_history() -> None:
    st.session_state.messages = []
    st.session_state.active_turn = None
    st.session_state.selected_source = None
    st.session_state.selected_excerpt = None


def load_turn(index: int) -> Dict[str, Any] | None:
    if 0 <= index < len(st.session_state.messages):
        st.session_state.active_turn = index
        turn: Dict[str, Any] = st.session_state.messages[index]
        return turn
    return None


def render_history_sidebar() -> None:
    st.sidebar.subheader("History")
    if st.sidebar.button("Clear history"):
        clear_history()
        st.rerun()
    if not st.session_state.messages:
        st.sidebar.caption("No queries yet.")
        return
    for i, msg in enumerate(reversed(st.session_state.messages)):
        real_idx = len(st.session_state.messages) - 1 - i
        label = f"{i + 1}. {msg['question'][:50]}"
        if st.sidebar.button(label, key=f"hist_{real_idx}"):
            load_turn(real_idx)
            st.rerun()
        if msg.get("answer"):
            st.sidebar.caption(msg["answer"][:60])
