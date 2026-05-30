# PersonalRAGVault

Local-first RAG system for your personal data.

Ingests files from your Downloads folder (emails, chats, invoices, codebases, tweets, PDFs, notes), embeds them with a lightweight CPU-friendly model, stores in a local vector database, and lets you query everything naturally using Ollama or other local LLMs.

Optimized for MacBook M1/M-series with pure CPU inference. No cloud. No limits on your personal history.

## Features (Planned)

- Watch or batch-ingest from `~/Downloads`
- Support for PDF, TXT, MD, JSON, chat exports, code files
- Small embedding model (~0.6B params) running on CPU
- ChromaDB local vector store
- Simple natural language query interface
- Optional Ollama integration for generation

## Quick Start

```bash
pip install -r requirements.txt
python -m src.cli ingest ~/Downloads
python -m src.cli query "find my notes about RAG systems"
```

## Status

Early scaffolding. Core ingestion + embedding + query loop in progress.