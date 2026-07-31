# PersonalRAGVault — Installation & Quick Start

## One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/seanebones-lang/personal-RAG/main/install.sh | bash
```

Or with a custom folder name:

```bash
curl -fsSL https://raw.githubusercontent.com/seanebones-lang/personal-RAG/main/install.sh | bash -s my-rag
```

## Manual Install

```bash
git clone https://github.com/seanebones-lang/personal-RAG.git
cd personal-RAG
./scripts/setup.sh
source .venv/bin/activate
```

## First-Time Setup

1. Run the doctor (highly recommended):

   ```bash
   personalragvault doctor
   ```

2. Pull an Ollama model (example):

   ```bash
   ollama pull qwen3-coder:30b
   # or
   ollama pull llama3.2
   ```

3. Set your generation model (optional):

   ```bash
   export PRV_OLLAMA_MODEL=qwen3-coder:30b
   ```

4. Verify:

   ```bash
   personalragvault status
   ```

## Usage Examples

```bash
# Ingest a folder
personalragvault ingest ~/Documents --recursive

# Ask questions
personalragvault query "What projects am I working on?"

# Launch web UI
personalragvault ui

# Start REST API
personalragvault serve
```

## Requirements

- macOS / Linux
- Python 3.10+
- Git
- Ollama (https://ollama.com)
- ~2–20 GB disk (depending on model)

## Troubleshooting

- Run `personalragvault doctor`
- Check `personalragvault status`
- See `docs/` for advanced configuration
