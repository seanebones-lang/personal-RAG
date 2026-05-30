"""Shared orchestration for CLI and UI."""

from src.core.vault import (
    get_status_info,
    run_ingest,
    run_purge,
    run_query,
)

__all__ = ["get_status_info", "run_ingest", "run_purge", "run_query"]
