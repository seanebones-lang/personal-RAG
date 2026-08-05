# PersonalRAGVault — CTO Backlog

Execution source of truth. Update checkboxes on ship. **v1.5.0** retrieval ship 2026-08-05.

## Wave 0 — Truth & alignment

- [x] Dual-tree: Desktop `main` aligned with origin before work
- [x] Baseline: ruff + pytest unit suite green
- [x] `run_query` signature has `hybrid` + `use_llm`
- [x] Agents roster + this backlog

## Wave 1 — Ingest hygiene + config coherence

- [x] **W1.1** Exclude noise dirs from discovery
- [x] **W1.2** `PRV_INGEST_EXCLUDE_DIRS`
- [x] **W1.3** `PRV_HYBRID` default CLI/API/UI
- [x] **W1.4** Unit tests discover excludes + hybrid settings
- [x] **W1.5** Docs + `.env.example`

## Wave 2 — API + serve hardening

- [x] **W2.1** Expand API tests (mocked)
- [x] **W2.2** `GET /version`
- [x] **W2.3** Optional `PRV_API_TOKEN`
- [x] **W2.4** Purge remains CLI-only (skip API mutate surface)
- [x] **W2.5** Serve OpenAPI URL + non-loopback warning

## Wave 3 — Quality / CI / coverage

- [x] **W3.1** CI unit-only + ruff src/tests
- [x] **W3.2** Coverage term in CI
- [x] **W3.3** Tests for W1–W2 + graph
- [x] **W3.4** LICENSE left alone (no relicense)

## Wave 4 — Retrieval / graph polish

- [x] **W4.1** CLI `graph` neighbors
- [x] **W4.2** Export wikilink edge list JSON
- [x] **W4.3** Status shows hybrid default + exclude count

## Wave 5 — Embed path experiment

- [ ] **W5.1** 📌 PINNED research — ONNX embed behind flag (high risk / heavy deps; demand-gated)

## Wave 6 — post-1.4 polish (1.4.1)

- [x] Silence Chroma telemetry spam
- [x] API `/graph/neighbors`
- [x] CLI hybrid default tests + graph tests
- [x] README v1.4 section

## Wave 7 — v1.5 retrieval that uses what we built

- [x] **W7.1** Wire FTS5 into hybrid RRF (BM25 fallback only)
- [x] **W7.2** Cache CrossEncoder singleton
- [x] **W7.3** Constant-time API token compare
- [x] **W7.4** multi_query ∘ hybrid composition
- [x] **W7.5** Parent expand via `get_by_where(parent_id)` (no 100k scan)
- [x] **W7.6** Query presets fast/balanced/quality (CLI/API/UI/env)
- [x] **W7.7** SSE `POST /query/stream`
- [x] **W7.8** Query-aware context compression
- [x] **W7.9** Chunk id content-hash scheme
- [x] **W7.10** API `allow_outside_home` env gate
- [x] **W7.11** Unit tests for FTS, parent, presets, stream, auth gate

## Done criteria (1.5)

- [x] Wave 7 eng items closed
- [ ] Unit suite green; ruff clean (verify in CI/local)
- [x] Roadmap/CHANGELOG honest; version **1.5.0**
- Residual: ONNX spike, browser history, HTML/CSV structure, desktop shell = product/research

## Wave 8 — planned 1.6

- [ ] Browser history opt-in parser
- [ ] HTML main-content + CSV structure parsers
- [ ] ONNX embed backend flag
- [ ] Golden eval set + citation-match metric
