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
| `--max-distance` | Drop chunks with distance above threshold |

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

Print chunk count, database path, embedding model, and Ollama settings.

```bash
personalragvault status
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

`.txt`, `.md`, `.pdf`, `.json`, `.docx`, `.py`, `.js`, `.ts`, `.html`, `.htm`, `.csv`, `.xml`, `.yaml`, `.yml`, `.rst`

---

## See also

- [Getting started](getting-started.md)
- [Configuration](configuration.md)
- [FAQ](faq.md)
