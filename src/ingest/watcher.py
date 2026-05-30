"""Watch folder for changes and re-ingest with debouncing."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class DebouncedIngestHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_trigger: Callable[[], None],
        debounce_seconds: float = 2.0,
        supported_suffixes: Optional[set[str]] = None,
    ) -> None:
        self._on_trigger = on_trigger
        self._debounce_seconds = debounce_seconds
        self._supported = supported_suffixes or set()
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        logger.info("Debounced watch triggered ingest")
        try:
            self._on_trigger()
        except Exception as exc:
            logger.error("Watch ingest failed: %s", exc)

    def _should_handle(self, path: str) -> bool:
        if not self._supported:
            return True
        return Path(path).suffix.lower() in self._supported

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._should_handle(str(event.src_path)):
            self._schedule()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._should_handle(str(event.src_path)):
            self._schedule()

    def on_moved(self, event: FileSystemEvent) -> None:
        dest = getattr(event, "dest_path", event.src_path)
        if not event.is_directory and self._should_handle(str(dest)):
            self._schedule()


def run_watch(
    folder: Path,
    on_trigger: Callable[[], None],
    debounce_seconds: float = 2.0,
    supported_suffixes: Optional[set[str]] = None,
) -> None:
    """Block and watch folder until KeyboardInterrupt."""
    handler = DebouncedIngestHandler(
        on_trigger=on_trigger,
        debounce_seconds=debounce_seconds,
        supported_suffixes=supported_suffixes,
    )
    observer = Observer()
    observer.schedule(handler, str(folder), recursive=False)
    observer.start()
    logger.info("Watching %s (Ctrl+C to stop)", folder)
    try:
        observer.join()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
