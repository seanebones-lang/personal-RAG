"""PersonalRAGVault CLI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.config import get_settings
from src.core.vault import (
    build_where_from_options,
    get_status_info,
    list_embed_presets,
    run_compact,
    run_ingest,
    run_purge,
    run_query,
)
from src.ingest.ingest import all_supported_extensions, validate_ingest_path
from src.ingest.watcher import run_watch

app = typer.Typer(help="PersonalRAGVault - Local personal RAG")
models_app = typer.Typer(help="Embedding model presets")
eval_app = typer.Typer(help="Retrieval evaluation")
app.add_typer(models_app, name="models")
app.add_typer(eval_app, name="eval")

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
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-ingest all files even if unchanged (ignore file cache)",
    ),
    chunk_strategy: Optional[str] = typer.Option(
        None,
        "--chunk-strategy",
        help="Override PRV_CHUNK_STRATEGY for this ingest only",
    ),
) -> None:
    """Ingest supported files from a directory."""
    if not _quiet:
        console.print(f"[bold green]Scanning[/bold green] {path}")
    try:
        count = run_ingest(
            path,
            recursive=recursive,
            allow_outside_home=allow_outside_home,
            force=force,
            show_progress=not _quiet,
            chunk_strategy=chunk_strategy,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if count == 0:
        if not _quiet:
            console.print("[yellow]No usable text found.[/yellow]")
        raise typer.Exit(code=1)
    if not _quiet:
        console.print(f"[bold green]Ingestion complete.[/bold green] ({count} chunks)")


@app.command()
def query(
    q: str = typer.Argument(..., help="Natural language question"),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1, help="Chunks to retrieve"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Retrieval only; do not call Ollama"),
    hybrid: bool = typer.Option(False, "--hybrid", help="BM25 + vector RRF fusion"),
    max_distance: Optional[float] = typer.Option(
        None,
        "--max-distance",
        help="Skip chunks with distance above this threshold",
    ),
    where_year: Optional[int] = typer.Option(None, "--where-year", help="Filter by metadata year"),
    source_contains: Optional[str] = typer.Option(
        None, "--source-contains", help="Filter sources containing substring"
    ),
    extension: Optional[str] = typer.Option(None, "--extension", help="Filter by file extension"),
    filter_json: Optional[str] = typer.Option(
        None, "--filter", help='Chroma where JSON, e.g. \'{"year": 2025}\''
    ),
    multi_query: bool = typer.Option(False, "--multi-query", help="Fuse multiple query variants"),
    expand_query: bool = typer.Option(
        False, "--expand-query", help="Use Ollama for extra query variants (with --multi-query)"
    ),
    rerank: bool = typer.Option(False, "--rerank", help="Cross-encoder rerank candidates"),
    parent_expand: bool = typer.Option(
        False, "--parent-expand", help="Expand hits with neighboring chunks"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write query results as JSON"
    ),
) -> None:
    """Query your personal knowledge base with RAG + Ollama."""
    settings = get_settings()
    if top_k > settings.max_top_k:
        _stderr.print(
            f"[red]Error:[/red] top_k cannot exceed {settings.max_top_k} (set PRV_MAX_TOP_K)"
        )
        raise typer.Exit(code=2)

    try:
        where = build_where_from_options(
            where_year=where_year,
            source_contains=source_contains,
            extension=extension,
            filter_json=filter_json,
        )
    except ValueError as exc:
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if _debug or not _quiet:
        console.print(f"[bold cyan]Query:[/bold cyan] {q}")
    elif not _quiet:
        console.print("[bold cyan]Running query...[/bold cyan]")

    try:
        out = run_query(
            q,
            top_k=top_k,
            max_distance=max_distance,
            where=where,
            hybrid=hybrid,
            use_llm=not no_llm,
            multi_query=multi_query,
            expand_query=expand_query,
            rerank=rerank,
            parent_expand=parent_expand,
        )
    except RuntimeError as exc:
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    results = out["results"]
    if not results:
        console.print("[yellow]No results found in your knowledge base.[/yellow]")
        raise typer.Exit(code=1)

    table = Table(title="Retrieved chunks")
    table.add_column("Source", style="dim")
    table.add_column("Score")
    table.add_column("Preview")
    for r in results:
        meta = r.get("metadata") or {}
        source = str(meta.get("source", meta.get("file_name", "?")))
        score = r.get("rrf_score")
        score_str = f"{score:.4f}" if score is not None else f"{r.get('distance', 0):.4f}"
        preview = (r["text"][:80] + "...") if len(r["text"]) > 80 else r["text"]
        table.add_row(source, score_str, preview)
    if not _quiet:
        console.print(table)

    if output:
        from src.export import export_turn_json

        output.write_text(
            export_turn_json(q, out.get("answer"), results),
            encoding="utf-8",
        )
        if not _quiet:
            console.print(f"[dim]Wrote {output}[/dim]")

    if no_llm:
        console.print("\n[bold]Context:[/bold]")
        console.print(out["context"])
        return

    if out["answer"]:
        console.print("\n[bold green]Answer:[/bold green]")
        console.print(out["answer"])
    elif out["llm_error"]:
        _stderr.print(f"[yellow]Ollama error:[/yellow] {out['llm_error']}")
        if _debug:
            console.print("\n[yellow]Raw retrieved context:[/yellow]")
            for r in results:
                text = r["text"]
                suffix = "..." if len(text) > 300 else ""
                console.print(f"- {text[:300]}{suffix}")
        raise typer.Exit(code=1)


@models_app.command("list")
def models_list() -> None:
    """List embedding model presets."""
    table = Table(title="Embedding presets")
    table.add_column("Preset")
    table.add_column("Model ID")
    table.add_column("Dim")
    table.add_column("RAM")
    table.add_column("Description")
    for row in list_embed_presets():
        table.add_row(
            row["name"],
            row["model_id"],
            str(row["dimensions"]),
            row["ram_note"],
            row["description"],
        )
    console.print(table)
    console.print("\nUse: export PRV_EMBED_PRESET=bge-small  (or PRV_EMBED_MODEL=...)")


@app.command()
def status() -> None:
    """Show vault status."""
    info = get_status_info()
    console.print("[bold]PersonalRAGVault status[/bold]")
    console.print(f"  Documents (chunks): {info.chunk_count}")
    console.print(f"  DB path: {info.db_path}")
    console.print(f"  Embed model: {info.embed_model}")
    if info.embed_preset:
        console.print(f"  Active preset: {info.embed_preset}")
    console.print(f"  Embed dimension: {info.embed_dim or 'not set'}")
    console.print(f"  Ollama: {info.ollama_host} / {info.ollama_model}")
    console.print(f"  Chunk strategy: {info.chunk_strategy}")
    console.print(f"  Chunk size / overlap: {info.chunk_size} / {info.chunk_overlap}")
    console.print(f"  HNSW search_ef: {info.hnsw_search_ef}")
    console.print(
        f"  Caches: file={info.use_file_cache} fts={info.use_fts} "
        f"embed={info.use_embedding_cache}"
    )
    if info.chunk_count > 5000:
        console.print(
            "[yellow]  Tip: large vault — try --hybrid and "
            "`personalragvault compact`[/yellow]"
        )
    for key, val in info.sidecar_stats.items():
        if key.endswith("_bytes"):
            console.print(f"  {key}: {val}")


@app.command()
def purge(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete all documents from the vector store."""
    if not yes:
        confirm = typer.confirm("Delete entire knowledge base?")
        if not confirm:
            raise typer.Exit()
    run_purge()
    console.print("[bold green]Knowledge base purged.[/bold green]")


@app.command(name="reindex")
def reindex_cmd(
    path: Path = typer.Argument(..., help="Folder to re-ingest"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    allow_outside_home: bool = typer.Option(False, "--allow-outside-home"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    force: bool = typer.Option(True, "--force", help="Force re-read all files"),
) -> None:
    """Purge the vault and re-ingest a folder."""
    if not yes:
        confirm = typer.confirm("Purge and re-ingest? This clears all stored chunks.")
        if not confirm:
            raise typer.Exit()
    run_purge()
    try:
        run_ingest(
            path,
            recursive=recursive,
            allow_outside_home=allow_outside_home,
            force=force,
            show_progress=not _quiet,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@eval_app.command("run")
def eval_run(
    dataset: Path = typer.Argument(..., help="JSONL evaluation dataset"),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1),
    hybrid: bool = typer.Option(False, "--hybrid"),
    multi_query: bool = typer.Option(False, "--multi-query"),
    expand_query: bool = typer.Option(False, "--expand-query"),
    rerank: bool = typer.Option(False, "--rerank"),
    parent_expand: bool = typer.Option(False, "--parent-expand"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write JSON results"),
) -> None:
    """Run retrieval evaluation (hit@k, MRR, NDCG@k)."""
    from src.eval.runner import run_evaluation

    payload = run_evaluation(
        dataset,
        top_k=top_k,
        hybrid=hybrid,
        multi_query=multi_query,
        expand_query=expand_query,
        rerank=rerank,
        parent_expand=parent_expand,
        output_json=output,
    )
    summary = payload["summary"]
    console.print("[bold]Evaluation summary[/bold]")
    console.print(f"  Cases: {int(summary['count'])}")
    console.print(f"  Hit@{top_k}: {summary['hit_at_k']:.2%}")
    console.print(f"  MRR: {summary['mrr']:.4f}")
    console.print(f"  NDCG@{top_k}: {summary['ndcg_at_k']:.4f}")
    if output:
        console.print(f"  Wrote {output}")


@eval_app.command("generate")
def eval_generate(
    path: Optional[Path] = typer.Argument(
        None, help="Folder to sample (if vault empty); else samples from vault"
    ),
    sample: int = typer.Option(10, "--sample", "-n", min=1),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Heuristic questions only"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    allow_outside_home: bool = typer.Option(False, "--allow-outside-home"),
) -> None:
    """Generate synthetic eval dataset (review before trusting)."""
    from src.eval.generate import generate_dataset, write_dataset

    rows = generate_dataset(
        path=path,
        sample=sample,
        use_ollama=not no_llm,
        recursive=recursive,
        allow_outside_home=allow_outside_home,
        from_vault=path is None,
    )
    if not rows:
        _stderr.print("[red]No chunks to sample. Ingest a folder first.[/red]")
        raise typer.Exit(code=1)
    write_dataset(rows, output)
    console.print(
        f"[yellow]Generated {len(rows)} cases — review {output} before running eval.[/yellow]"
    )


@app.command()
def compact() -> None:
    """Maintain sidecar indexes (file cache orphans, FTS rebuild)."""
    stats = run_compact()
    console.print("[bold green]Compact complete.[/bold green]")
    for key, val in stats.items():
        console.print(f"  {key}: {val}")


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
        run_ingest(
            folder,
            recursive=recursive,
            allow_outside_home=allow_outside_home,
            show_progress=not _quiet,
        )

    run_ingest(
        folder,
        recursive=recursive,
        allow_outside_home=allow_outside_home,
        show_progress=not _quiet,
    )

    run_watch(
        folder,
        on_trigger=trigger,
        debounce_seconds=debounce,
        supported_suffixes=all_supported_extensions(),
    )


@app.command()
def ui(
    port: int = typer.Option(8501, "--port", help="Streamlit port"),
) -> None:
    """Launch local web UI (requires pip install personalragvault[ui])."""
    try:
        import streamlit.web.cli as stcli
    except ImportError as exc:
        _stderr.print("[red]Streamlit not installed.[/red] Run: pip install personalragvault[ui]")
        raise typer.Exit(code=1) from exc

    import sys
    from pathlib import Path as P

    app_path = P(__file__).parent / "ui" / "app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
    ]
    stcli.main()


def main_entry() -> None:
    app()


if __name__ == "__main__":
    main_entry()
