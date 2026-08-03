# Roadmap

PersonalRAGVault evolves in phased releases. **v1.4** hardens ingest/API defaults and ships lightweight wikilink graph ops.

## Shipped

| Version | Highlights |
|---------|------------|
| **v0.2** | Chunking, hybrid search, eml/mbox, filters, file cache, FTS, Streamlit MVP |
| **v0.3** | Eval harness (Hit@k, MRR), UI components, recursive/semantic chunking, HNSW, Telegram/Obsidian |
| **v1.0** | NDCG, `eval generate`, `semantic_embed`, multi-query, rerank, parent expand, UI export/chat |
| **v1.1–1.2** | Doctor, config TOML, streaming answers, OCR, WhatsApp/Notion/bookmarks/ICS, reranker presets |
| **v1.3** | FastAPI `serve`, response cache, EPUB, streaming batch ingest, dry-run, Obsidian wikilinks |
| **v1.4** | Ingest noise excludes, `PRV_HYBRID` defaults, API token/version, `graph` CLI, CI harden |

## v1.4 (current)

- **Ingest:** skip `.obsidian`/`.git`/caches/… + `PRV_INGEST_EXCLUDE_DIRS`
- **Defaults:** `PRV_HYBRID` for CLI/API/UI (`--hybrid/--no-hybrid`)
- **API:** `GET /version`, optional `PRV_API_TOKEN`, serve docs URL + bind warnings
- **Graph:** `personalragvault graph <note>` + `--export-edges` over wikilink metadata
- **CI:** unit-only pytest + ruff on `src tests` + coverage term

## Planned

| Release | Focus |
|---------|--------|
| **v1.5** | ONNX / faster CPU embed path experiment (feature-flag); browser history opt-in |
| **v2.0** | Desktop shell (if demand), plugin parser API, richer graph query |

## Out of scope

- Cloud-hosted API or multi-tenant SaaS
- Default remote embeddings or telemetry

See [CTO_BACKLOG.md](CTO_BACKLOG.md), [evaluation.md](evaluation.md), [filtering.md](filtering.md), [large-vaults.md](large-vaults.md), [community.md](community.md), and [sources/](sources/).
