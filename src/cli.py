"""PersonalRAGVault CLI."""

from __future__ import annotations

import logging
import shutil
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
    preview_ingest,
    run_compact,
    run_ingest,
    run_purge,
    run_query,
)
from src.diagnostics import check_large_vault_recommendations, run_full_diagnostics
from src.ingest.ingest import all_supported_extensions, validate_ingest_path
from src.ingest.watcher import run_watch
from src.ollama_client import extract_citations
from src.retrieval.reranker_presets import list_reranker_presets

app = typer.Typer(help="PersonalRAGVault - Local personal RAG")
models_app = typer.Typer(help="Embedding model presets")
eval_app = typer.Typer(help="Retrieval evaluation")
config_app = typer.Typer(help="Configuration (env + optional TOML file)")
rerankers_app = typer.Typer(help="Reranker model presets")

app.add_typer(models_app, name="models")
app.add_typer(eval_app, name="eval")
app.add_typer(config_app, name="config")
app.add_typer(rerankers_app, name="rerankers")

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
        help="Override PRV_CHUNK_STRATEGY for this ingest only (warning: semantic_embed is slow)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview files/chunk estimate without embedding or writing",
    ),
) -> None:
    """Ingest supported files from a directory."""
    if dry_run:
        try:
            preview = preview_ingest(
                path,
                recursive=recursive,
                allow_outside_home=allow_outside_home,
                force=force,
            )
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            _stderr.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=2) from exc
        console.print("[bold cyan]Ingest dry-run[/bold cyan]")
        console.print(f"  Files discovered: {preview['files_discovered']}")
        console.print(f"  Would process:    {preview['files_to_process']}")
        console.print(f"  Unchanged skip:   {preview['files_unchanged_skip']}")
        console.print(f"  Est. chunks:      ~{preview['estimated_chunks']}")
        if preview["sample_paths"]:
            console.print("  Sample paths:")
            for p in preview["sample_paths"]:
                console.print(f"    • {p}")
        return

    if not _quiet:
        console.print(f"[bold green]Scanning[/bold green] {path}")

    progress = None
    file_task = None
    chunk_task = None
    if not _quiet:
        try:
            from rich.progress import (
                BarColumn,
                MofNCompleteColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
                TimeElapsedColumn,
            )

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            )
            progress.start()
            file_task = progress.add_task("Files", total=None)
            chunk_task = progress.add_task("Chunks upserted", total=None)
        except Exception:
            progress = None

    def _on_progress(stage: str, current: int, total: int, meta: dict) -> None:
        if progress is None:
            return
        if stage == "file" and file_task is not None:
            if total:
                progress.update(
                    file_task,
                    completed=current,
                    total=total,
                    description=f"Files ({meta.get('path', '')[-40:]})",
                )
            else:
                progress.update(file_task, completed=current)
        elif stage == "embed_upsert" and chunk_task is not None:
            progress.update(chunk_task, completed=current, total=max(total, current))

    try:
        count = run_ingest(
            path,
            recursive=recursive,
            allow_outside_home=allow_outside_home,
            force=force,
            show_progress=not _quiet and progress is None,
            chunk_strategy=chunk_strategy,
            progress_callback=_on_progress if progress is not None else None,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        if progress is not None:
            progress.stop()
        _stderr.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    finally:
        if progress is not None:
            progress.stop()

    if count == 0:
        if not _quiet:
            console.print("[yellow]No usable text found.[/yellow]")
        raise typer.Exit(code=1)
    if not _quiet:
        console.print(f"[bold green]Ingestion complete.[/bold green] ({count} chunks)")
        if count > 15000:
            console.print(
                "[dim]Large vault tip: run `personalragvault compact` "
                "and see docs/large-vaults.md[/dim]"
            )
    if chunk_strategy and "semantic_embed" in str(chunk_strategy).lower():
        console.print(
            "[yellow]Note: semantic_embed chunking was used. This is high-quality but CPU-heavy. "
            "Run `personalragvault doctor` if you see performance issues.[/yellow]"
        )


@app.command()
def query(
    q: str = typer.Argument(..., help="Natural language question"),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1, help="Chunks to retrieve"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Retrieval only; do not call Ollama"),
    hybrid: Optional[bool] = typer.Option(
        None,
        "--hybrid/--no-hybrid",
        help="BM25 + vector RRF fusion (default: PRV_HYBRID)",
    ),
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
    preset: Optional[str] = typer.Option(
        None,
        "--preset",
        help="Query quality preset: fast | balanced | quality (or PRV_QUERY_PRESET)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write query results as JSON"
    ),
) -> None:
    """Query your personal knowledge base with RAG + Ollama."""
    settings = get_settings()
    use_hybrid = settings.hybrid_default if hybrid is None else hybrid
    use_preset = preset if preset is not None else settings.query_preset
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
            hybrid=use_hybrid,
            use_llm=not no_llm,
            multi_query=multi_query,
            expand_query=expand_query,
            rerank=rerank,
            parent_expand=parent_expand,
            stream=not no_llm and not _quiet,   # beautiful streaming by default in interactive CLI
            preset=use_preset,
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

    # Streaming path for excellent UX (token by token)
    stream_gen = out.get("answer_stream")
    if stream_gen:
        console.print("\n[bold green]Answer:[/bold green]", end="")
        full_answer = ""
        for token in stream_gen:
            console.print(token, end="")
            full_answer += token
        console.print()  # newline

        # Timings (note: generation time is not accurate in pure stream mode yet)
        timings = out.get("timings") or {}
        if timings and not _quiet:
            parts = []
            if timings.get("retrieval") is not None:
                parts.append(f"retrieval {timings['retrieval']}s")
            if timings.get("total"):
                parts.append(f"total {timings['total']}s")
            console.print(f"[dim]⏱  {' | '.join(parts)}[/dim]")

        citations = extract_citations(full_answer)
        if citations and not _quiet:
            console.print("\n[dim]Sources cited:[/dim]")
            for c in citations[:8]:
                console.print(f"  [dim]•[/dim] {c}")
        return

    # Fallback non-streaming path
    if out["answer"]:
        console.print("\n[bold green]Answer:[/bold green]")
        console.print(out["answer"])

        timings = out.get("timings") or {}
        if timings:
            parts = []
            if timings.get("retrieval") is not None:
                parts.append(f"retrieval {timings['retrieval']}s")
            if timings.get("generation"):
                parts.append(f"generation {timings['generation']}s")
            if timings.get("total"):
                parts.append(f"total {timings['total']}s")
            if parts and not _quiet:
                console.print(f"[dim]⏱  {' | '.join(parts)}[/dim]")

        citations = extract_citations(out["answer"])
        if citations and not _quiet:
            console.print("\n[dim]Sources cited:[/dim]")
            for c in citations[:8]:
                console.print(f"  [dim]•[/dim] {c}")
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
    console.print(
        "\n[dim]Reranking: Set PRV_RERANK=true and optionally PRV_RERANK_PRESET=... "
        "(mini | tiny | bge). See `personalragvault rerankers list`[/dim]"
    )


@rerankers_app.command("list")
def rerankers_list() -> None:
    """List available reranker presets (lightweight options for local use)."""
    table = Table(title="Reranker Presets")
    table.add_column("Preset")
    table.add_column("Model ID")
    table.add_column("Size")
    table.add_column("Description")
    table.add_column("Best For")

    for row in list_reranker_presets():
        table.add_row(
            row["name"],
            row["model_id"],
            row["size"],
            row["description"],
            row["recommended_for"],
        )

    console.print(table)
    console.print("\nUsage:")
    console.print("  export PRV_RERANK_PRESET=mini   # or tiny / bge")
    console.print("  export PRV_RERANK=true")
    console.print("\n[dim]Install with: pip install \"personalragvault[retrieval]\"[/dim]")


@app.command("presets")
def query_presets_list() -> None:
    """List query quality presets (fast / balanced / quality)."""
    from src.retrieval.presets import list_query_presets

    table = Table(title="Query quality presets")
    table.add_column("Preset")
    table.add_column("Hybrid")
    table.add_column("Multi")
    table.add_column("Rerank")
    table.add_column("Parent")
    table.add_column("Description")
    for row in list_query_presets():
        table.add_row(
            row["name"],
            "✓" if row["hybrid"] else "·",
            "✓" if row["multi_query"] else "·",
            "✓" if row["rerank"] else "·",
            "✓" if row["parent_expand"] else "·",
            row["description"],
        )
    console.print(table)
    console.print("\nUsage:")
    console.print("  personalragvault query \"...\" --preset balanced")
    console.print("  export PRV_QUERY_PRESET=balanced")


@config_app.command("show")
def config_show() -> None:
    """Show effective configuration (env vars + loaded TOML file)."""
    from src.config import get_settings

    s = get_settings()
    console.print("[bold]Effective configuration[/bold]\n")
    console.print(f"  DB path: {s.db_path}")
    console.print(f"  Embed model: {s.embed_model} (preset={s.embed_preset})")
    console.print(f"  Chunk strategy: {s.chunk_strategy}")
    console.print(f"  Ollama: {s.ollama_host} / {s.ollama_model}")
    console.print(f"  Max context chars: {s.max_context_chars}")
    console.print("\n[dim]Advanced retrieval defaults can be overridden per-query.[/dim]")
    console.print(
        "[dim]Config file loaded from ~/.personalragvault/config.toml "
        "or PRV_CONFIG_PATH (env vars always win)[/dim]"
    )


@config_app.command("edit")
def config_edit() -> None:
    """Open the config file in your editor (creates a helpful template if missing)."""
    import os
    import subprocess
    from pathlib import Path

    default_cfg = "~/.personalragvault/config.toml"
    config_path = Path(os.environ.get("PRV_CONFIG_PATH") or default_cfg).expanduser()

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        template = """# PersonalRAGVault configuration
# This file is loaded in addition to environment variables (env vars win).

[core]
# embed_model = "bge-small"
# chunk_strategy = "prose"
# ollama_model = "llama3.2"

[retrieval]
# multi_query = true
# rerank = true
# hybrid = true
"""
        config_path.write_text(template, encoding="utf-8")
        console.print(f"[green]Created template config at {config_path}[/green]")

    editor = os.environ.get("EDITOR")
    if not editor:
        # Sensible macOS/Linux fallbacks
        for candidate in ["code", "subl", "nano", "vim", "open -t"]:
            if candidate == "open -t":
                editor = candidate
                break
            if shutil.which(candidate.split()[0]):
                editor = candidate
                break
    if not editor:
        editor = "nano"

    console.print(f"Opening {config_path} with {editor}...")

    try:
        if editor == "open -t":
            subprocess.run(["open", "-t", str(config_path)], check=False)
        else:
            subprocess.run([*editor.split(), str(config_path)], check=False)
    except Exception as exc:
        _stderr.print(f"[red]Failed to open editor:[/red] {exc}")
        console.print(f"You can edit it manually at: {config_path}")


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
    console.print(f"  Caches: file={info.use_file_cache} fts={info.use_fts} "
        f"embed={info.use_embedding_cache} response={info.response_cache_enabled}"
    )
    if info.use_fts:
        console.print(
            "  [dim]FTS: wired into hybrid search (vector + FTS RRF; BM25 fallback)[/dim]"
        )
    qp = get_settings().query_preset
    if qp:
        console.print(f"  Query preset default: {qp}")
    console.print(
        f"  Defaults: hybrid={info.hybrid_default} "
        f"ingest_exclude_dirs={info.ingest_exclude_dir_count}"
    )
    if info.response_cache_stats:
        s = info.response_cache_stats
        console.print(
            f"  Response cache: hits={s.get('hits', 0)} misses={s.get('misses', 0)} "
            f"size={s.get('size', 0)}"
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
def doctor() -> None:
    """Run health checks and diagnostics (highly recommended after model changes)."""
    info = get_status_info()
    console.print("[bold cyan]PersonalRAGVault Doctor[/bold cyan]\n")

    results = run_full_diagnostics(chunk_count=info.chunk_count)

    for r in results:
        icon = "[green]✓[/green]" if r.ok else "[red]✗[/red]"
        console.print(f"{icon} {r.name}: {r.message}")
        if r.detail:
            console.print(f"    [dim]{r.detail}[/dim]")

    # First-time setup guidance
    if info.chunk_count == 0:
        console.print("\n[bold yellow]First-time setup tips:[/bold yellow]")
        console.print("  1. Pull a model:  ollama pull qwen3-coder:30b  (or llama3.2)")
        console.print("  2. Set model:     export PRV_OLLAMA_MODEL=qwen3-coder:30b")
        console.print("  3. Ingest data:   personalragvault ingest ~/Documents --recursive")
        console.print("  4. Launch UI:     personalragvault ui")

    # Large vault tips
    tips = check_large_vault_recommendations(info.chunk_count)
    if tips:
        console.print("\n[yellow]Recommendations for your vault size:[/yellow]")
        for t in tips:
            console.print(f"  • {t}")

    if info.chunk_count > 8000:
        console.print(
            "\n[dim]For detailed scaling guidance, see: docs/large-vaults.md[/dim]"
        )

    # Final summary
    failures = [r for r in results if not r.ok]
    if failures:
        console.print(f"\n[red]Found {len(failures)} issue(s) that should be addressed.[/red]")
    else:
        console.print("\n[green]All core checks passed.[/green]")


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
    hybrid: Optional[bool] = typer.Option(None, "--hybrid/--no-hybrid"),
    multi_query: bool = typer.Option(False, "--multi-query"),
    expand_query: bool = typer.Option(False, "--expand-query"),
    rerank: bool = typer.Option(False, "--rerank"),
    parent_expand: bool = typer.Option(False, "--parent-expand"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write JSON results"),
) -> None:
    """Run retrieval evaluation (hit@k, MRR, NDCG@k)."""
    from src.eval.runner import run_evaluation

    use_hybrid = get_settings().hybrid_default if hybrid is None else hybrid
    payload = run_evaluation(
        dataset,
        top_k=top_k,
        hybrid=use_hybrid,
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


@app.command("graph")
def graph_cmd(
    note: Optional[str] = typer.Argument(
        None, help="Note name (stem) for neighbors; omit with --export-edges"
    ),
    direction: str = typer.Option(
        "both", "--direction", "-d", help="out | in | both (default both)"
    ),
    export_edges: Optional[Path] = typer.Option(
        None, "--export-edges", help="Write wikilink edge list JSON and exit"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Max corpus rows to scan (default hybrid fetch limit)"
    ),
) -> None:
    """Obsidian wikilink neighbors / edge export from vault metadata."""
    from src.retrieval.graph import export_edges_json, neighbors

    if export_edges is not None:
        n = export_edges_json(export_edges, limit=limit)
        console.print(f"[green]Wrote {n} edges to {export_edges}[/green]")
        return
    if not note:
        _stderr.print("[red]Error:[/red] pass a note name or --export-edges PATH")
        raise typer.Exit(code=2)
    d = direction.strip().lower()
    if d not in ("out", "in", "both"):
        _stderr.print("[red]Error:[/red] --direction must be out, in, or both")
        raise typer.Exit(code=2)
    result = neighbors(note, direction=d, limit=limit)
    console.print(f"[bold]Note:[/bold] {result['note']}")
    if result.get("source"):
        console.print(f"[dim]{result['source']}[/dim]")
    console.print(f"Outbound ({len(result['outbound'])}): {', '.join(result['outbound']) or '—'}")
    console.print(f"Inbound  ({len(result['inbound'])}): {', '.join(result['inbound']) or '—'}")
    console.print(
        f"[dim]Indexed notes≈{result['notes_indexed']} edges={result['edges']}[/dim]"
    )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (default localhost only)"),
    port: int = typer.Option(8765, "--port", help="HTTP port"),
    reload: bool = typer.Option(False, "--reload", help="Dev auto-reload"),
) -> None:
    """Run local FastAPI HTTP API (query/ingest/status). Localhost by default."""
    if host not in ("127.0.0.1", "localhost", "::1") and not _quiet:
        console.print(
            "[bold yellow]Warning:[/bold yellow] binding outside localhost "
            f"([cyan]{host}[/cyan]) exposes your vault over the network. "
            "Set [cyan]PRV_API_TOKEN[/cyan] (Bearer) before non-loopback use."
        )
    try:
        import uvicorn
    except ImportError as exc:
        _stderr.print("[red]uvicorn not installed.[/red] Reinstall package deps.")
        raise typer.Exit(code=1) from exc

    if not _quiet:
        base = f"http://{host}:{port}"
        console.print(f"[bold green]API[/bold green] {base}")
        console.print(f"  Docs: [link={base}/docs]{base}/docs[/link]")
        console.print("  GET /health  GET /version  GET /status")
        console.print("  POST /query  POST /ingest  GET|POST /cache/*")
    uvicorn.run("src.query.api:app", host=host, port=port, reload=reload, log_level="info")


def main_entry() -> None:
    import logging
    import warnings

    warnings.filterwarnings("ignore", message="capture() takes")
    # Chroma may still log telemetry failures even when disabled
    for name in (
        "chromadb.telemetry",
        "chromadb.telemetry.product.posthog",
        "posthog",
    ):
        logging.getLogger(name).setLevel(logging.CRITICAL)
        logging.getLogger(name).disabled = True
    app()


if __name__ == "__main__":
    main_entry()
