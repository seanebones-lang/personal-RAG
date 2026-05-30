"""PersonalRAGVault CLI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.config import get_settings
from src.embed.embedder import embed_query, embed_texts
from src.ingest.ingest import SUPPORTED_EXTENSIONS, validate_ingest_path
from src.ingest.pipeline import build_documents_from_folder
from src.ingest.watcher import run_watch
from src.ollama_client import build_context, check_ollama_model, generate_answer
from src.store.vectorstore import (
    count_documents,
    delete_by_sources,
    purge_collection,
    search,
    upsert_documents,
)

app = typer.Typer(help="PersonalRAGVault - Local personal RAG")
console = Console()
_stderr = Console(stderr=True)

_verbose = False
_quiet = False
_debug = False


def _setup_logging(verbose: bool, quiet: bool) -> None:
    level = logging.WARNING
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )


def _run_ingest(
    path: Path,
    recursive: bool,
    allow_outside_home: bool,
    show_progress: bool = True,
) -> int:
    try:
        docs = build_documents_from_folder(
            path,
            recursive=recursive,
            allow_outside_home=allow_outside_home,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if not docs:
        if not _quiet:
            console.print("[yellow]No usable text found.[/yellow]")
        return 0

    sources = list({d["metadata"]["source"] for d in docs})
    delete_by_sources(sources)

    if not _quiet:
        console.print(f"Embedding {len(docs)} chunks from {len(sources)} file(s)...")

    texts = [d["text"] for d in docs]
    embeddings = embed_texts(texts, show_progress=show_progress and not _quiet)
    for i, doc in enumerate(docs):
        doc["embedding"] = embeddings[i]

    upsert_documents(docs)
    if not _quiet:
        console.print("[bold green]Ingestion complete.[/bold green]")
    return len(docs)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Info logging"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
    debug: bool = typer.Option(False, "--debug", help="Show sensitive debug output"),
) -> None:
    global _verbose, _quiet, _debug
    _verbose = verbose
    _quiet = quiet
    _debug = debug
    _setup_logging(verbose, quiet)


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="Folder to ingest"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Scan subdirectories"),
    allow_outside_home: bool = typer.Option(
        False,
        "--allow-outside-home",
        help="Allow ingesting paths outside home directory",
    ),
) -> None:
    """Ingest supported files from a directory."""
    if not _quiet:
        console.print(f"[bold green]Scanning[/bold green] {path}")
    count = _run_ingest(path, recursive=recursive, allow_outside_home=allow_outside_home)
    if count == 0:
        raise typer.Exit(code=1)


@app.command()
def query(
    q: str = typer.Argument(..., help="Natural language question"),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1, help="Chunks to retrieve"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Retrieval only; do not call Ollama"),
    max_distance: Optional[float] = typer.Option(
        None,
        "--max-distance",
        help="Skip chunks with distance above this threshold",
    ),
) -> None:
    """Query your personal knowledge base with RAG + Ollama."""
    settings = get_settings()
    if top_k > settings.max_top_k:
        _stderr.print(
            f"[red]Error:[/red] top_k cannot exceed {settings.max_top_k} (set PRV_MAX_TOP_K)"
        )
        raise typer.Exit(code=2)

    if _debug or not _quiet:
        console.print(f"[bold cyan]Query:[/bold cyan] {q}")
    elif not _quiet:
        console.print("[bold cyan]Running query...[/bold cyan]")

    query_embedding = embed_query(q)
    results = search(query_embedding, top_k=top_k, max_distance=max_distance)

    if not results:
        console.print("[yellow]No results found in your knowledge base.[/yellow]")
        raise typer.Exit(code=1)

    table = Table(title="Retrieved chunks")
    table.add_column("Source", style="dim")
    table.add_column("Distance")
    table.add_column("Preview")
    for r in results:
        meta = r.get("metadata") or {}
        source = str(meta.get("source", "?"))
        preview = (r["text"][:80] + "...") if len(r["text"]) > 80 else r["text"]
        table.add_row(source, f"{r['distance']:.4f}", preview)
    if not _quiet:
        console.print(table)

    context = build_context(results, settings.max_context_chars)

    if no_llm:
        console.print("\n[bold]Context:[/bold]")
        console.print(context)
        return

    if not _quiet:
        console.print(f"[dim]Generating answer with {settings.ollama_model}...[/dim]")

    try:
        check_ollama_model()
        prompt = f"""You are a helpful assistant with access to the user's personal knowledge base.
Use the following context to answer the question. If the answer is not in the context, say so.

Context:
{context}

Question: {q}

Answer:"""
        answer = generate_answer(prompt)
        console.print("\n[bold green]Answer:[/bold green]")
        console.print(answer)
    except Exception as exc:
        _stderr.print(f"[yellow]Ollama error:[/yellow] {exc}")
        if _debug:
            console.print("\n[yellow]Raw retrieved context:[/yellow]")
            for r in results:
                text = r["text"]
                suffix = "..." if len(text) > 300 else ""
                snippet = text[:300] + suffix
                console.print(f"- {snippet}")
        raise typer.Exit(code=1) from exc


@app.command()
def status() -> None:
    """Show vault status."""
    settings = get_settings()
    n = count_documents()
    console.print("[bold]PersonalRAGVault status[/bold]")
    console.print(f"  Documents (chunks): {n}")
    console.print(f"  DB path: {settings.db_path}")
    console.print(f"  Embed model: {settings.embed_model}")
    console.print(f"  Ollama: {settings.ollama_host} / {settings.ollama_model}")
    console.print(f"  Chunk size / overlap: {settings.chunk_size} / {settings.chunk_overlap}")


@app.command()
def purge(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete all documents from the vector store."""
    if not yes:
        confirm = typer.confirm("Delete entire knowledge base?")
        if not confirm:
            raise typer.Exit()
    purge_collection()
    console.print("[bold green]Knowledge base purged.[/bold green]")


@app.command(name="reindex")
def reindex_cmd(
    path: Path = typer.Argument(..., help="Folder to re-ingest"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    allow_outside_home: bool = typer.Option(False, "--allow-outside-home"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Purge the vault and re-ingest a folder."""
    if not yes:
        confirm = typer.confirm("Purge and re-ingest? This clears all stored chunks.")
        if not confirm:
            raise typer.Exit()
    purge_collection()
    _run_ingest(path, recursive=recursive, allow_outside_home=allow_outside_home)


@app.command()
def watch(
    path: Path = typer.Argument(..., help="Folder to watch"),
    debounce: float = typer.Option(2.0, "--debounce", help="Seconds to debounce events"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    allow_outside_home: bool = typer.Option(False, "--allow-outside-home"),
) -> None:
    """Watch a folder and re-ingest on file changes."""
    try:
        folder = validate_ingest_path(path, allow_outside_home=allow_outside_home)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    def trigger() -> None:
        _run_ingest(folder, recursive=recursive, allow_outside_home=allow_outside_home)

    _run_ingest(folder, recursive=recursive, allow_outside_home=allow_outside_home)

    run_watch(
        folder,
        on_trigger=trigger,
        debounce_seconds=debounce,
        supported_suffixes=SUPPORTED_EXTENSIONS,
    )


def main_entry() -> None:
    app()


if __name__ == "__main__":
    main_entry()
