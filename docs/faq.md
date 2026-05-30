# FAQ

## Install and setup

### Why does `pip install -e ".[dev]"` fail?

You are probably not in the project root. `ls pyproject.toml` must work. See [Getting started](getting-started.md).

### Why is `personalragvault` command not found?

1. Activate the venv: `source .venv/bin/activate`
2. Reinstall: `pip install -e ".[dev]"`
3. Use: `python -m src.cli status`

### Can I use Python 3.14?

The project targets 3.10–3.12 in CI. Newer Python may work but dependencies (e.g. Chroma) can emit warnings or errors. Prefer 3.10–3.12 for stability.

## Usage

### Ingest found 0 files

- Check extensions in [CLI reference](cli-reference.md)
- By default only **top-level** files are scanned; use `--recursive`
- Empty PDFs or failed extraction produce no chunks — run with `--verbose`

### Query returns no results

- Run `personalragvault status` — chunk count must be &gt; 0
- Ingest first: `personalragvault ingest ~/your-folder`

### Do I need `--allow-outside-home` for `~/Downloads`?

No. `~/Downloads` is under your home directory. Use the flag only for paths like `/tmp` or external mounts outside `$HOME`.

### How do I avoid duplicate chunks when re-ingesting?

Re-run `ingest` on the same folder. The tool deletes chunks for touched sources and upserts fresh ones.

### How do I switch embedding or Ollama models?

Set `PRV_EMBED_MODEL` or `OLLAMA_MODEL`. After changing the embed model, **purge and re-ingest**. See [Configuration](configuration.md).

## Ollama

### Ollama connection errors

- Start Ollama (app or `ollama serve`)
- Check `OLLAMA_HOST`
- Pull the model: `ollama pull llama3.2`

### I do not want to use Ollama

```bash
personalragvault query "your question" --no-llm
```

## Data and privacy

### Where is my data stored?

Vectors and chunk text: `PRV_DB_PATH` (default `~/.personalragvault/chroma`). Original files are never copied—only paths in metadata.

### Does anything go to the cloud?

Not by default. The embedding model may download from Hugging Face on first use. Ollama runs locally. No telemetry is sent by this app’s Chroma config.

### How do I back up?

Copy the `PRV_DB_PATH` directory while the CLI is not writing to it.

### How do I delete everything?

```bash
personalragvault purge --yes
```

Or remove `~/.personalragvault/chroma` manually.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [Development](development.md).
