# Roadmap

PersonalRAGVault evolves in phased releases. **v1.5** wires FTS into hybrid retrieval, ships query presets, and hardens the API stream path.

## Shipped

| Version | Highlights |
|---------|------------|
| **v0.2** | Chunking, hybrid search, eml/mbox, filters, file cache, FTS, Streamlit MVP |
| **v0.3** | Eval harness (Hit@k, MRR), UI components, recursive/semantic chunking, HNSW, Telegram/Obsidian |
| **v1.0** | NDCG, `eval generate`, `semantic_embed`, multi-query, rerank, parent expand, UI export/chat |
| **v1.1–1.2** | Doctor, config TOML, streaming answers, OCR, WhatsApp/Notion/bookmarks/ICS, reranker presets |
| **v1.3** | FastAPI `serve`, response cache, EPUB, streaming batch ingest, dry-run, Obsidian wikilinks |
| **v1.4** | Ingest noise excludes, `PRV_HYBRID` defaults, API token/version, `graph` CLI, CI harden |
| **v1.5** | FTS→hybrid RRF, query presets, SSE `/query/stream`, parent-by-metadata, multi∘hybrid, rerank cache |

## v1.5 (current)

- **Hybrid:** vector + FTS5 RRF (BM25 only as fallback); no full-corpus BM25 when FTS is warm
- **Presets:** `fast` / `balanced` / `quality` (`--preset`, `PRV_QUERY_PRESET`, UI, API)
- **API:** `POST /query/stream` SSE, `GET /presets`, constant-time bearer compare, outside-home gate
- **Scale:** parent expand via `parent_id` filter; CrossEncoder singleton
- **Quality:** query-aware context compression; multi-query can run hybrid per variant

## Planned

| Release | Focus |
|---------|--------|
| **v1.6** | ONNX / faster CPU embed path experiment (feature-flag); browser history opt-in; HTML/CSV structure |
| **v2.0** | Desktop shell (if demand), plugin parser API, richer graph query |

## Out of scope

- Cloud-hosted API or multi-tenant SaaS
- Default remote embeddings or telemetry

See [CTO_BACKLOG.md](CTO_BACKLOG.md), [evaluation.md](evaluation.md), [filtering.md](filtering.md), [large-vaults.md](large-vaults.md), [community.md](community.md), and [sources/](sources/).
