# Getting started

PersonalRAGVault is a **local-only** CLI: your files stay on your machine, embeddings run on CPU, and answers can use a local [Ollama](https://ollama.com/) model.

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | Check with `python3 --version` |
| **Git** | To clone the repository |
| **Disk space** | ~500MB+ for Python deps; more for the embedding model cache |
| **Ollama** (optional) | Required for generated answers; skip with `--no-llm` |

## 1. Clone the repository

```bash
git clone https://github.com/seanebones-lang/probable-fishstick.git
cd probable-fishstick
```

Use your fork URL if you cloned a fork.

## 2. Create a virtual environment (in the project)

**Important:** run all commands from the directory that contains `pyproject.toml`. Do not create `.venv` in your home folder.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

Or use the helper script:

```bash
./scripts/setup.sh
source .venv/bin/activate
```

## 3. Install

**End users:**

```bash
pip install -r requirements.txt
# or
pip install -e .
```

**Contributors (includes pytest, ruff, mypy):**

```bash
pip install -e ".[dev]"
```

Verify the CLI:

```bash
personalragvault status
# fallback if PATH issues:
python -m src.cli status
```

## 4. Set up Ollama (optional)

```bash
# Install from https://ollama.com/ then:
ollama pull llama3.2
```

Use a different model by setting `OLLAMA_MODEL` (see [Configuration](configuration.md)).

## 5. Ingest your files

Put or point at a folder with supported files (PDF, TXT, MD, JSON, DOCX, code, etc.):

```bash
personalragvault ingest ~/Downloads
```

Options:

- `--recursive` / `-r` — include subfolders
- `--verbose` / `-v` — show extraction warnings
- `--allow-outside-home` — if the folder is not under `$HOME`

First ingest downloads the embedding model from Hugging Face and may take several minutes.

## 6. Query

```bash
personalragvault query "What notes do I have about RAG?"
```

Retrieval only (no Ollama):

```bash
personalragvault query "summarize my PDFs" --no-llm
```

## 7. Watch a folder (optional)

Automatically re-ingest when files change:

```bash
personalragvault watch ~/Downloads --debounce 2.0
```

Press `Ctrl+C` to stop.

## What gets stored where

| Data | Default location |
|------|------------------|
| Vector database (ChromaDB) | `~/.personalragvault/chroma` |
| Embedding model cache | Hugging Face / sentence-transformers cache under your user dir |

Override the DB path with `PRV_DB_PATH` — see [Configuration](configuration.md).

## Next steps

- [CLI reference](cli-reference.md) — all commands and flags
- [Configuration](configuration.md) — tune chunk size, models, limits
- [FAQ](faq.md) — troubleshooting
