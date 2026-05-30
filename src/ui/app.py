"""PersonalRAGVault local Streamlit UI — localhost only."""

from __future__ import annotations

import streamlit as st

from src.config import CHUNK_STRATEGIES
from src.core.vault import (
    build_where_from_options,
    get_status_info,
    list_embed_presets,
    run_compact,
    run_ingest,
    run_purge,
    run_query,
)
from src.ui.components.export_ui import render_export_buttons
from src.ui.components.preview import render_preview_panel
from src.ui.components.results import render_results
from src.ui.components.session import add_turn, init_session, load_turn, render_history_sidebar

st.set_page_config(page_title="PersonalRAGVault", page_icon="🔒", layout="wide")
init_session()

st.title("PersonalRAGVault")
st.caption("Local-only. Data stays on your machine. Do not expose this port to the network.")

render_history_sidebar()

tab_status, tab_ingest, tab_query, tab_models, tab_maintenance = st.tabs(
    ["Status", "Ingest", "Query", "Models", "Maintenance"]
)

with tab_status:
    info = get_status_info()
    st.metric("Chunks", info.chunk_count)
    c1, c2, c3 = st.columns(3)
    c1.metric("File cache (bytes)", info.sidecar_stats.get("file_cache_bytes", 0))
    c2.metric("FTS (bytes)", info.sidecar_stats.get("fts_bytes", 0))
    c3.metric("Embed cache (bytes)", info.sidecar_stats.get("embedding_cache_bytes", 0))
    st.json(
        {
            "db_path": info.db_path,
            "embed_model": info.embed_model,
            "embed_dim": info.embed_dim,
            "chunk_strategy": info.chunk_strategy,
            "hnsw_search_ef": info.hnsw_search_ef,
            "ollama": f"{info.ollama_host} / {info.ollama_model}",
        }
    )
    if st.button("Purge vault", type="primary"):
        run_purge()
        st.success("Vault purged.")
        st.rerun()

with tab_ingest:
    ingest_path = st.text_input("Folder path", value="~/Downloads")
    col1, col2 = st.columns(2)
    with col1:
        recursive = st.checkbox("Recursive")
        force = st.checkbox("Force re-ingest (ignore file cache)")
    with col2:
        allow_outside = st.checkbox("Allow outside home")
    strategies = sorted(CHUNK_STRATEGIES)
    chunk_pick = st.selectbox(
        "Chunk strategy (this ingest)",
        options=["(default from env)"] + strategies,
    )
    chunk_strategy = None if chunk_pick == "(default from env)" else chunk_pick
    if st.button("Ingest"):
        try:
            from pathlib import Path

            with st.spinner("Ingesting..."):
                n = run_ingest(
                    Path(ingest_path).expanduser(),
                    recursive=recursive,
                    allow_outside_home=allow_outside,
                    force=force,
                    show_progress=False,
                    chunk_strategy=chunk_strategy,
                )
            st.success(f"Ingested {n} chunks.")
        except Exception as exc:
            st.error(str(exc))

with tab_query:
    top_k = st.slider("Top K", 1, 20, 5)
    hybrid = st.checkbox("Hybrid search (BM25 + vector)")
    no_llm = st.checkbox("Retrieval only (no Ollama)")
    multi_query = st.checkbox("Multi-query fusion")
    rerank = st.checkbox("Cross-encoder rerank")
    parent_expand = st.checkbox("Parent document expand")
    with st.expander("Filters"):
        where_year = st.number_input(
            "Year (0 = any)",
            min_value=0,
            max_value=2100,
            value=0,
            step=1,
        )
        where_year_val = int(where_year) if where_year >= 1990 else None
        source_contains = st.text_input("Source contains")
        extension = st.text_input("Extension (e.g. .pdf)")

    col_main, col_preview = st.columns([2, 1])

    def _run_search(question: str) -> None:
        if not question.strip():
            st.warning("Enter a question.")
            return
        try:
            where = build_where_from_options(
                where_year=where_year_val,
                source_contains=source_contains or None,
                extension=extension or None,
            )
            with st.spinner("Searching..."):
                out = run_query(
                    question,
                    top_k=top_k,
                    where=where,
                    hybrid=hybrid,
                    use_llm=not no_llm,
                    multi_query=multi_query,
                    rerank=rerank,
                    parent_expand=parent_expand,
                )
            add_turn(question, out.get("answer"), out["results"])
            st.session_state.last_query_out = out
        except Exception as exc:
            st.error(str(exc))

    with col_main:
        if hasattr(st, "chat_input"):
            question = st.chat_input("Ask about your vault…")
            if question:
                _run_search(question)
        else:
            question = st.text_input("Question", placeholder="What do my notes say about…")
            if st.button("Search") and question:
                _run_search(question)

        active = None
        if st.session_state.active_turn is not None:
            active = load_turn(st.session_state.active_turn)
        elif st.session_state.messages:
            active = st.session_state.messages[-1]

        if active:
            st.chat_message("user").write(active["question"])
            if active.get("answer"):
                st.chat_message("assistant").write(active["answer"])
            results = active.get("results", [])

            def _select(src: str, excerpt: str) -> None:
                st.session_state.selected_source = src
                st.session_state.selected_excerpt = excerpt

            render_results(results, on_select=_select)
            render_export_buttons(
                active["question"],
                active.get("answer"),
                results,
            )

    with col_preview:
        render_preview_panel(
            st.session_state.selected_source,
            st.session_state.get("selected_excerpt"),
        )

with tab_models:
    st.table(list_embed_presets())
    st.info("Set PRV_EMBED_PRESET=mini|bge-small|bge-base or PRV_EMBED_MODEL=… then re-ingest.")

with tab_maintenance:
    st.write("Rebuild sidecar indexes and remove orphaned file-cache rows.")
    if st.button("Run compact"):
        stats = run_compact()
        st.success(f"Compact complete: {stats}")
