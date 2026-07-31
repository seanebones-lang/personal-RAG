# Roadmap

PersonalRAGVault evolves in phased releases. **v1.3** focuses on API surface, large-ingest safety, caching, and Obsidian graph metadata.

## Shipped

| Version | Highlights |
|---------|------------|
| **v0.2** | Chunking, hybrid search, eml/mbox, filters, file cache, FTS, Streamlit MVP |
| **v0.3** | Eval harness (Hit@k, MRR), UI components, recursive/semantic chunking, HNSW, Telegram/Obsidian |
| **v1.0** | NDCG, `eval generate`, `semantic_embed`, multi-query, rerank, parent expand, UI export/chat |
| **v1.1–1.2** | Doctor, config TOML, streaming answers, OCR, WhatsApp/Notion/bookmarks/ICS, reranker presets |
| **v1.3** | FastAPI `serve`, response cache, EPUB, streaming batch ingest, dry-run, Obsidian wikilinks |

## v1.3 (current)

- **API:** `personalragvault serve` — local FastAPI (`/query`, `/ingest`, `/status`, `/health`)
- **Ingest:** streaming batch upsert (`PRV_INGEST_BATCH_SIZE`), `--dry-run`, Rich progress
- **Cache:** query response cache (`PRV_RESPONSE_CACHE*`), auto-invalidate on ingest/purge
- **Sources:** EPUB parser (stdlib fallback + optional `ebooklib`), Obsidian wikilink metadata
- **Reliability:** fixed `run_query` hybrid/use_llm regression from intermediate cache wiring

## Planned

| Release | Focus |
|---------|--------|
| **v1.4** | ONNX / faster CPU embed path experiment; browser history opt-in |
| **v2.0** | Desktop shell (if demand), plugin parser API, full Obsidian graph query |

## Out of scope

- Cloud-hosted API or multi-tenant SaaS
- Default remote embeddings or telemetry

See [evaluation.md](evaluation.md), [filtering.md](filtering.md), [large-vaults.md](large-vaults.md), [community.md](community.md), and [sources/](sources/).
