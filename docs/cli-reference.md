# CLI reference

Entry points:

```bash
personalragvault <command> [options]
python -m src.cli <command> [options]
```

Global options (before the subcommand):

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

**Example:**

```bash
personalragvault ingest ~/Downloads -r --verbose
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
| `--hybrid` | BM25 + vector RRF fusion |
| `--max-distance` | Drop chunks with distance above threshold |
| `--where-year` | Filter by metadata year |
| `--source-contains` | Filter sources containing substring |
| `--extension` | Filter by file extension |
| `--filter` | Raw Chroma `where` JSON |

**Examples:**

```bash
personalragvault query "invoices from Acme Corp"
personalragvault query "python asyncio patterns" --top-k 10 --no-llm
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

Runs until `Ctrl+C`. Performs an initial ingest on start.

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
personalragvault eval run ./my_eval.jsonl [--top-k 5] [--hybrid] [-o results.json]
```

---

## `ui`

Launch the local Streamlit app (`personalragvault[ui]`).

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

## Supported file extensions

Defined in `src/ingest/ingest.py`:

`.txt`, `.md`, `.pdf`, `.json`, `.docx`, `.py`, `.js`, `.ts`, `.html`, `.htm`, `.csv`, `.xml`, `.yaml`, `.yml`, `.rst`, `.eml`, `.mbox`

Telegram exports (`result.json`) and Obsidian `.md` notes use dedicated parsers — see [sources/](sources/).

---

## See also

- [Getting started](getting-started.md)
- [Configuration](configuration.md)
- [FAQ](faq.md)
