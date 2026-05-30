"""PersonalRAGVault local Streamlit UI — localhost only."""

from __future__ import annotations

import streamlit as st

from src.core.vault import (
    build_where_from_options,
    get_status_info,
    list_embed_presets,
    run_ingest,
    run_purge,
    run_query,
)

st.set_page_config(page_title="PersonalRAGVault", page_icon="🔒", layout="wide")
st.title("PersonalRAGVault")
st.caption("Local-only. Data stays on your machine. Do not expose this port to the network.")

tab_status, tab_ingest, tab_query, tab_models = st.tabs(
    ["Status", "Ingest", "Query", "Models"]
)

with tab_status:
    info = get_status_info()
    st.metric("Chunks", info.chunk_count)
    st.json(
        {
            "db_path": info.db_path,
            "embed_model": info.embed_model,
            "embed_dim": info.embed_dim,
            "ollama": f"{info.ollama_host} / {info.ollama_model}",
            "file_cache": info.use_file_cache,
            "fts": info.use_fts,
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
    if st.button("Ingest"):
        try:
            from pathlib import Path

            n = run_ingest(
                Path(ingest_path).expanduser(),
                recursive=recursive,
                allow_outside_home=allow_outside,
                force=force,
                show_progress=False,
            )
            st.success(f"Ingested {n} chunks.")
        except Exception as exc:
            st.error(str(exc))

with tab_query:
    question = st.text_input("Question", placeholder="What do my notes say about…")
    top_k = st.slider("Top K", 1, 20, 5)
    hybrid = st.checkbox("Hybrid search (BM25 + vector)")
    no_llm = st.checkbox("Retrieval only (no Ollama)")
    with st.expander("Filters"):
        where_year = st.number_input("Year", min_value=1990, max_value=2100, value=0, step=1)
        where_year_val = int(where_year) if where_year > 0 else None
        source_contains = st.text_input("Source contains")
        extension = st.text_input("Extension (e.g. .pdf)")

    if st.button("Search"):
        if not question.strip():
            st.warning("Enter a question.")
        else:
            try:
                where = build_where_from_options(
                    where_year=where_year_val,
                    source_contains=source_contains or None,
                    extension=extension or None,
                )
                out = run_query(
                    question,
                    top_k=top_k,
                    where=where,
                    hybrid=hybrid,
                    use_llm=not no_llm,
                )
                for i, r in enumerate(out["results"], 1):
                    meta = r.get("metadata") or {}
                    st.markdown(f"**{i}.** `{meta.get('source', '?')}`")
                    st.text(r["text"][:500])
                if out["answer"]:
                    st.subheader("Answer")
                    st.write(out["answer"])
                elif out["llm_error"]:
                    st.warning(out["llm_error"])
                    st.text_area("Context", out["context"], height=200)
            except Exception as exc:
                st.error(str(exc))

with tab_models:
    st.table(list_embed_presets())
    st.info("Set PRV_EMBED_PRESET=mini|bge-small|bge-base or PRV_EMBED_MODEL=… then re-ingest.")
