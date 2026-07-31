# Personal-RAG max optimization wave — 2026-07-31

## Critical fix
- Restored `hybrid` + `use_llm` on `run_query` (regression from half-wired response cache broke CLI/UI/eval)

## Shipped in v1.3.0
1. Streaming batch ingest (`iter_file_documents` + `PRV_INGEST_BATCH_SIZE`)
2. `ingest --dry-run`
3. Rich multi-batch embed + CLI ingest progress
4. `personalragvault serve` FastAPI (localhost)
5. Response cache with full key space + invalidate on mutate
6. EPUB parser + Obsidian wikilink metadata
7. Tests + docs + roadmap honesty

## Verify
```bash
pip install -e ".[dev]"
ruff check src tests
pytest -m "not integration"
```
