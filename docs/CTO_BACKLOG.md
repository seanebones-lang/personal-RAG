# PersonalRAGVault — CTO Backlog

Execution source of truth. Update checkboxes on ship. **v1.4.0** swarm ship 2026-08-03.

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

## Done criteria

- [x] Waves 1–4 eng items closed
- [x] Unit suite green; ruff clean
- [x] Roadmap/CHANGELOG honest; version **1.4.0**
- Residual: ONNX spike, browser history, desktop shell = product/research only
