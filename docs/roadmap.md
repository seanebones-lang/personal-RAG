# Roadmap

PersonalRAGVault evolves in six tracks. Release mapping is a guide, not a strict schedule.

## Tracks

| Track | Theme | Status |
|-------|--------|--------|
| 1 | Embedding presets, dimension guard, `models list` | Shipped in v0.2 |
| 2 | Parser registry, `.eml` / `.mbox` | Shipped in v0.2 |
| 3 | Rich metadata, filtered queries | Shipped in v0.2 |
| 4 | Hybrid search (BM25 + vector RRF) | Shipped in v0.2 |
| 5 | File hash cache, batch embed, FTS sidecar, `compact` | Shipped in v0.2 |
| 6 | Optional Streamlit UI (`pip install .[ui]`) | Shipped in v0.2 |

## Release mapping

| Release | Focus |
|---------|--------|
| **v0.2** | Tracks 1–6 (foundation for advanced personal RAG) |
| **v0.3** | WhatsApp/Telegram parsers, query-smart filters, FTS at scale |
| **v0.4** | Sentence-aware chunking, Chroma tuning |
| **v0.5** | Tauri/desktop UI (if demand) |

## Out of scope

- Cloud-hosted API or multi-tenant SaaS
- Default remote embeddings or telemetry
- Breaking default MiniLM behavior without a major version

## Contributing

Pick an issue labeled `embedding`, `ingest`, `metadata`, `retrieval`, `performance`, or `ui`. See [CONTRIBUTING.md](../CONTRIBUTING.md).
