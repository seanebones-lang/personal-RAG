# Roadmap

PersonalRAGVault evolves in phased releases. v0.2 shipped the core production CLI; **v0.3** adds measurement, UI polish, advanced chunking, scale tuning, and new data sources.

## Shipped

| Version | Highlights |
|---------|------------|
| **v0.2** | Chunking, hybrid search, eml/mbox, filters, file cache, FTS, Streamlit MVP |
| **v0.3** | Eval harness, UI components, recursive/semantic chunking, HNSW config, embedding cache, Telegram/Obsidian parsers |

## v0.3 features (current)

- **UI:** Result cards, conversation history sidebar, document preview, maintenance tab
- **Chunking:** `PRV_CHUNK_STRATEGY=char|recursive|semantic`; markdown/code-aware splits
- **Scale:** `PRV_HNSW_SEARCH_EF`, `PRV_HNSW_M`, embedding cache, paginated hybrid fetch
- **Sources:** Telegram `result.json`, Obsidian frontmatter/tags on `.md`
- **Eval:** `personalragvault eval run --dataset eval.jsonl`

## Planned

| Release | Focus |
|---------|--------|
| **v0.4** | WhatsApp/Notion parsers, `st.chat_input` UI, query-smart filters |
| **v0.5** | Semantic splitter improvements, browser history (opt-in) |
| **v0.6** | Optional ONNX quantization, desktop shell (if demand) |

## Out of scope

- Cloud-hosted API or multi-tenant SaaS
- Default remote embeddings or telemetry

See [evaluation.md](evaluation.md), [filtering.md](filtering.md), and [sources/](sources/).
