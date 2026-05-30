# Roadmap

PersonalRAGVault evolves in phased releases. **v1.0** ships evaluation depth, advanced retrieval, chunking flexibility, and UI export/chat polish.

## Shipped

| Version | Highlights |
|---------|------------|
| **v0.2** | Chunking, hybrid search, eml/mbox, filters, file cache, FTS, Streamlit MVP |
| **v0.3** | Eval harness (Hit@k, MRR), UI components, recursive/semantic chunking, HNSW, Telegram/Obsidian |
| **v1.0** | NDCG, `eval generate`, `semantic_embed`, multi-query, rerank, parent expand, UI export/highlight/chat |

## v1.0 features (current)

- **Eval:** NDCG@k, `eval generate`, retrieval flags on `eval run`
- **Chunking:** `semantic_embed`, `PRV_CHUNK_STRATEGY_BY_EXT`, `--chunk-strategy` on ingest
- **Retrieval:** `--multi-query`, `--rerank`, `--parent-expand` (env defaults off)
- **UI:** `st.chat_input`, history restore, excerpt highlight, JSON/Markdown export
- **Community:** GitHub topics guide, demo recording instructions

## Planned

| Release | Focus |
|---------|--------|
| **v1.1** | WhatsApp/Notion parsers, wikilink graph for Obsidian |
| **v1.2** | Browser history (opt-in), ONNX embed experiment |
| **v2.0** | Desktop shell (if demand), plugin parser API |

## Out of scope

- Cloud-hosted API or multi-tenant SaaS
- Default remote embeddings or telemetry

See [evaluation.md](evaluation.md), [filtering.md](filtering.md), [community.md](community.md), and [sources/](sources/).
