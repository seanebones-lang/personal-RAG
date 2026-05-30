import time
from unittest.mock import MagicMock

from src.ingest.watcher import DebouncedIngestHandler


def test_debounced_handler_fires_once():
    calls = []

    def on_trigger():
        calls.append(1)

    handler = DebouncedIngestHandler(on_trigger=on_trigger, debounce_seconds=0.2)
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/tmp/test.txt"

    handler.on_modified(event)
    handler.on_modified(event)
    time.sleep(0.35)
    assert len(calls) == 1
