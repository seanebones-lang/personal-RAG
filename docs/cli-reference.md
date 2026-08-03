# CLI reference

Entry points:

```bash
personalragvault <command> [options]
python -m src.cli <command> [options]
```

## Global options

Global options must appear **before** the subcommand (Typer callback):

```bash
# Correct
personalragvault -q query "hello" --no-llm
personalragvault -v ingest ~/notes --recursive

# Wrong — `-q` is not a query option
personalragvault query "hello" -q
```

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | INFO logging |
| `--quiet` / `-q` | Minimal output |
| `--debug` | Show sensitive fallback context on Ollama errors |

Exit codes: `0` success, `1` operational failure, `2` usage/validation error.

---

## `ingest`

Ingest supported files from a directory into the vector store.

```bash
personalragvault ingest PATH [options]
```

| Option | Description |
|--------|-------------|
| `--recursive` / `-r` | Scan subdirectories |
| `--allow-outside-home` | Allow paths outside `$HOME` |
| `--force` | Re-ingest even if file cache says unchanged |
| `--chunk-strategy` | Override `PRV_CHUNK_STRATEGY` for this ingest |
| `--dry-run` | Count files + estimate chunks; no embed/write |

Ingest streams file → embed → upsert batches (`PRV_INGEST_BATCH_SIZE`, default 500) with Rich progress.

### Directory excludes

Recursive discovery skips paths whose components match built-in noise directory names (case-sensitive path parts):

`.obsidian`, `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.hg`, `.svn`, `.idea`, `.vscode`.

Add more names with `PRV_INGEST_EXCLUDE_DIRS` (comma-separated). Matching is by **directory name component**, not full path. Non-recursive ingest only lists files in the top folder (excludes mainly matter with `-r`). See [configuration.md](configuration.md).

**Example:**

```bash
export PRV_INGEST_EXCLUDE_DIRS=vendor,dist
personalragvault ingest ~/Documents/Vault -r --verbose
personalragvault ingest ~/Documents/Vault --recursive --dry-run
```

---

## `query`

Search the vault and optionally generate an answer with Ollama.

```bash
personalragvault query "QUESTION" [options]
```

| Option | Description |
|--------|-------------|
| `--top-k` / `-k` | Number of chunks to retrieve (default: 5, max: `PRV_MAX_TOP_K`) |
| `--no-llm` | Print retrieved context only |
| `--hybrid` | BM25 + vector RRF fusion (API also defaults from `PRV_HYBRID`; see configuration) |
| `--max-distance` | Drop chunks with distance above threshold |
| `--where-year` | Filter by metadata year |
| `--source-contains` | Filter sources containing substring |
| `--extension` | Filter by file extension |
| `--filter` | Raw Chroma `where` JSON |
| `--multi-query` | Fuse multiple query variants (RRF) |
| `--expand-query` | Ollama query rewrite (with `--multi-query`) |
| `--rerank` | Cross-encoder rerank |
| `--parent-expand` | Expand hits with sibling chunks |
| `--output` / `-o` | Write results JSON |

`PRV_HYBRID=true` sets `Settings.hybrid_default`. The HTTP API applies that default when `hybrid` is omitted from `POST /query`. CLI still accepts explicit `--hybrid`.

**Examples:**

```bash
personalragvault query "invoices from Acme Corp"
personalragvault -q query "python asyncio patterns" --top-k 10 --no-llm
personalragvault query "roadmap" --hybrid --no-llm
```

---

## `watch`

Watch a folder and re-ingest on file changes (debounced).

```bash
personalragvault watch PATH [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--debounce` | `2.0` | Seconds to wait after last change |
| `--recursive` / `-r` | off | Passed through to ingest |
| `--allow-outside-home` | off | Path validation override |

Runs until `Ctrl+C`. Performs an initial ingest on start. Same exclude-dir rules as `ingest` apply when scanning recursively.

---

## `status`

Print chunk count, database path, embedding model, chunk strategy, HNSW settings, and cache flags.

```bash
personalragvault status
```

---

## `compact`

Maintain sidecar indexes (orphan file-cache rows, FTS rebuild).

```bash
personalragvault compact
```

---

## `models list`

List embedding presets (`PRV_EMBED_PRESET`).

```bash
personalragvault models list
```

---

## `eval run`

Measure retrieval quality on a JSONL dataset (hit@k, MRR). See [evaluation.md](evaluation.md).

```bash
personalragvault eval run ./my_eval.jsonl [--top-k 5] [--hybrid] [--rerank] [-o results.json]
personalragvault eval generate --output draft.jsonl [--sample 20]
personalragvault eval generate ~/notes --output draft.jsonl --no-llm
```

Metrics: Hit@k, MRR, NDCG@k.

---

## `ui`

Launch the local Streamlit app (`personalragvault[ui]`). Binds `127.0.0.1`.

```bash
personalragvault ui [--port 8501]
```

---

## `purge`

Delete all chunks from the collection.

```bash
personalragvault purge [--yes]
```

Use `--yes` / `-y` to skip confirmation.

---

## `reindex`

Purge the vault, then ingest a folder from scratch.

```bash
personalragvault reindex PATH [--recursive] [--allow-outside-home] [--yes]
```

---

## `serve`

Local FastAPI HTTP API (localhost by default).

**Endpoints:** `GET /health`, `GET /status`, `GET /version` (package version), `POST /query`, `POST /ingest`, `GET /cache/stats`, `POST /cache/clear`. OpenAPI UI: `http://HOST:PORT/docs`.

```bash
personalragvault serve [--host 127.0.0.1] [--port 8765] [--reload]
```

### Security

- **Default bind is loopback** (`127.0.0.1`). Prefer this for day-to-day use.
- Binding outside localhost (`0.0.0.0`, LAN IP, etc.) prints a warning and reminds you to set `PRV_API_TOKEN`.
- Optional `PRV_API_TOKEN` (off by default — local-first): when non-empty, protected routes expect `Authorization: Bearer <token>`. **`GET /health` and `GET /version` stay public.** A token is not a full security boundary; do not expose the API to untrusted networks without additional hardening.
- Startup prints base URL + OpenAPI docs link (`/docs`).
- Ingest and query can read local paths and your vault contents — treat the port like shell access to your notes.

**Examples:**

```bash
personalragvault serve
personalragvault serve --host 127.0.0.1 --port 8765
# OpenAPI
open http://127.0.0.1:8765/docs

export PRV_API_TOKEN=change-me
curl -s http://127.0.0.1:8765/version
curl -s -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"question":"hello","use_llm":false}' \
  http://127.0.0.1:8765/query
```

---

## Supported file extensions

Defined in `src/ingest/ingest.py` + parser registry:

`.txt`, `.md`, `.pdf`, `.json`, `.docx`, `.py`, `.js`, `.ts`, `.html`, `.htm`, `.csv`, `.xml`, `.yaml`, `.yml`, `.rst`, `.eml`, `.mbox`, `.ics`, `.epub`, plus WhatsApp/Notion/bookmark exports and optional OCR images.

Telegram exports (`result.json`) and Obsidian `.md` notes use dedicated parsers — see [sources/](sources/).

---

## See also

- [Getting started](getting-started.md)
- [Configuration](configuration.md)
- [FAQ](faq.md)
- [Large vaults](large-vaults.md)
