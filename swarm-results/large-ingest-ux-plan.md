# Large Vault Ingest UX Improvements Plan

**Date**: 2026-07-31
**Context**: Review of docs/large-vaults.md (query-focused) + src/ingest/* and embed/embedder.py for Personal-RAG large vault ingest UX.

## Current State Findings
- `build_documents_from_folder` (pipeline.py): Sequential file processing, no progress reporting, loads all docs into memory.
- `run_ingest` (vault.py): Calls build then _attach_embeddings; uses show_progress flag.
- `embed_texts` (embedder.py): Uses `embed_batch_size` (config), sentence-transformers `show_progress_bar` (only first batch shown for large sets). Basic batching exists.
- CLI ingest: Simple "Scanning" + final count message; relies on library progress.
- No file-level progress, no memory streaming, no ETA/batching UI for >10k chunk ingests.
- large-vaults.md: Excellent for queries/retrieval (hybrid, filters, compact), silent on ingest UX.

## Recommended UX Enhancements (Priority Order)

### 1. Rich Progress Bars & Reporting (High)
- Integrate `rich.progress` (already in deps via cli) for:
  - File discovery/processing stage: "Processing 1,234/5,678 files"
  - Embedding stage: Per-batch + overall ETA using `Progress` with columns (description, bar, percentage, time remaining).
- Replace/supplement sentence-transformers bar with custom Rich bar that shows across all batches.
- Add stats: "X files skipped (unchanged)", "Y chunks generated", memory usage snapshot.

### 2. Streaming / Batching for Memory Management (High)
- Refactor `build_documents_from_folder` to be a generator yielding docs in batches (e.g., 500-1000 chunks).
- Process-embed-upsert in streaming pipeline to avoid OOM on 50k+ chunk vaults.
- Config: `PRV_INGEST_BATCH_SIZE` (default 1000 chunks).
- Memory guard: Monitor RSS, pause/suggest `compact` if > threshold.

### 3. Large Ingest Specific Features (Medium)
- `--dry-run` / preview mode: Show file count, estimated chunks, time projection.
- Incremental resume: Better handling of partial failures (track last processed file).
- Background mode hint or watcher integration for very large jobs.
- Post-ingest: Auto-suggest `doctor` + `compact` for large results (>15k chunks).

### 4. Updates to large-vaults.md (Low)
- Add "Ingesting Large Vaults" section with the above.
- Ingestion benchmarks (extend existing ones).
- Memory tuning tips.

## Implementation Roadmap (Wave 2+)
1. Patch embedder.py: Full Rich progress across batches + config-driven.
2. Update pipeline.py + vault.py: Streaming generator + batch upsert.
3. Enhance cli.py ingest command with rich Progress context.
4. Add tests for large ingest simulation.
5. Document in swarm-results and update large-vaults.md.

**Expected Impact**: Makes 30k+ chunk ingests feel responsive and safe (no silent hangs, visible progress, lower peak RAM).

Store this plan + any code patches in swarm-results/.