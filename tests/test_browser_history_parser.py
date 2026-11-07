"""Tests for the browser history parser (Backlog Wave 8, opt-in).

Fixture stores are real SQLite databases built inside the tests with
fictional URLs and titles only — no browser profile is ever read.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.config import reset_settings
from src.ingest.ingest import discover_files
from src.ingest.parsers.browser_history import BrowserHistoryParser
from src.ingest.parsers.registry import (
    extract_documents,
    registered_extensions,
    registered_filenames,
    reset_registry_for_tests,
)

_CHROMIUM_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


def _chromium_micros(moment: datetime) -> int:
    return int((moment - _CHROMIUM_EPOCH).total_seconds() * 1_000_000)


def _unix_micros(moment: datetime) -> int:
    return int(moment.timestamp() * 1_000_000)


def _make_chromium_store(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT,"
        " visit_count INTEGER, last_visit_time INTEGER)"
    )
    conn.executemany(
        "INSERT INTO urls (url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?)",
        [
            (
                "https://lantern-almanac.example/autumn",
                "The Lantern Keeper's Almanac",
                4,
                _chromium_micros(datetime(2026, 11, 5, 14, 25, tzinfo=timezone.utc)),
            ),
            (
                "https://tidecharts.example/harbor",
                "",
                1,
                _chromium_micros(datetime(2026, 11, 2, 8, 10, tzinfo=timezone.utc)),
            ),
            (
                "https://ferry-schedules.example/",
                "Harbor Ferry Schedules",
                9,
                _chromium_micros(datetime(2026, 11, 6, 19, 45, tzinfo=timezone.utc)),
            ),
        ],
    )
    conn.commit()
    conn.close()
    return path


def _make_firefox_store(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url TEXT,"
        " title TEXT, visit_count INTEGER, last_visit_date INTEGER,"
        " hidden INTEGER DEFAULT 0)"
    )
    conn.executemany(
        "INSERT INTO moz_places"
        " (url, title, visit_count, last_visit_date, hidden)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (
                "https://kiln-notes.example/firing-log",
                "Kiln Notes - Firing Log",
                3,
                _unix_micros(datetime(2026, 11, 3, 11, 5, tzinfo=timezone.utc)),
                0,
            ),
            # Internal pseudo-URL: browser plumbing, not a visit.
            (
                "place:sort=8&maxResults=10",
                "internal",
                5,
                _unix_micros(datetime(2026, 11, 4, tzinfo=timezone.utc)),
                0,
            ),
            # Hidden entries are redirect/frame targets, not pages read.
            (
                "https://hidden.example/redirect",
                "redirect target",
                2,
                _unix_micros(datetime(2026, 11, 4, tzinfo=timezone.utc)),
                1,
            ),
            # Never actually visited.
            ("https://never-visited.example/", "never", 0, None, 0),
        ],
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()


def _opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRV_INGEST_BROWSER_HISTORY", "true")
    reset_settings()
    reset_registry_for_tests()


def test_chromium_store_yields_one_document_per_url_most_recent_first(tmp_path):
    path = _make_chromium_store(tmp_path / "History")
    docs = BrowserHistoryParser().extract(path)

    assert len(docs) == 3
    first = docs[0]
    assert "History: Harbor Ferry Schedules" in first.text
    assert "URL: https://ferry-schedules.example/" in first.text
    assert "Visited: 2026-11-06 19:45" in first.text
    assert "Visits: 9" in first.text
    assert first.extra_metadata["format"] == "browser_history"
    assert first.extra_metadata["browser"] == "chromium"
    assert first.extra_metadata["visit_count"] == 9
    assert first.extra_metadata["last_visit"] == "2026-11-06 19:45"
    assert docs[1].extra_metadata["title"] == "The Lantern Keeper's Almanac"


def test_chromium_empty_title_falls_back_to_url_headline(tmp_path):
    path = _make_chromium_store(tmp_path / "History")
    docs = BrowserHistoryParser().extract(path)

    untitled = docs[2]
    assert untitled.extra_metadata["url"] == "https://tidecharts.example/harbor"
    assert "History: https://tidecharts.example/harbor" in untitled.text


def test_firefox_store_skips_internal_and_unvisited_rows(tmp_path):
    path = _make_firefox_store(tmp_path / "places.sqlite")
    docs = BrowserHistoryParser().extract(path)

    assert len(docs) == 1
    doc = docs[0]
    assert "History: Kiln Notes - Firing Log" in doc.text
    assert "Visited: 2026-11-03 11:05" in doc.text
    assert doc.extra_metadata["browser"] == "firefox"
    assert doc.extra_metadata["visit_count"] == 3


def test_missing_file_returns_no_documents(tmp_path):
    assert BrowserHistoryParser().extract(tmp_path / "History") == []


def test_corrupt_store_returns_no_documents(tmp_path):
    path = tmp_path / "places.sqlite"
    path.write_bytes(b"this is not a sqlite database at all")
    assert BrowserHistoryParser().extract(path) == []


def test_sqlite_database_without_history_tables_is_declined(tmp_path):
    path = tmp_path / "notes.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE notes (body TEXT)")
    conn.execute("INSERT INTO notes VALUES ('a perfectly good database')")
    conn.commit()
    conn.close()
    assert BrowserHistoryParser().extract(path) == []


def test_locked_store_is_read_via_copy_and_original_untouched(tmp_path):
    path = _make_chromium_store(tmp_path / "History")
    original_bytes = path.read_bytes()

    locker = sqlite3.connect(path)
    locker.execute("BEGIN EXCLUSIVE")
    try:
        docs = BrowserHistoryParser().extract(path)
    finally:
        locker.rollback()
        locker.close()

    assert len(docs) == 3
    # The original store is never opened by the parser: bytes unchanged
    # and no journal/WAL sidecar files were created beside it.
    assert path.read_bytes() == original_bytes
    assert sorted(p.name for p in tmp_path.iterdir()) == ["History"]


def test_opt_in_off_registry_and_discovery_skip_history_stores(tmp_path):
    history = _make_chromium_store(tmp_path / "History")
    places = _make_firefox_store(tmp_path / "places.sqlite")

    assert ".sqlite" not in registered_extensions()
    assert registered_filenames() == frozenset()
    # Even handed the file directly, the registry declines it — and
    # never falls back to wrapping the binary store as plain text.
    assert extract_documents(history, "fallback text") == []
    assert extract_documents(places, "fallback text") == []
    assert discover_files(tmp_path) == []


def test_opt_in_on_routes_both_stores_and_discovers_them(tmp_path, monkeypatch):
    history = _make_chromium_store(tmp_path / "History")
    places = _make_firefox_store(tmp_path / "places.sqlite")
    _opt_in(monkeypatch)

    assert ".sqlite" in registered_extensions()
    assert registered_filenames() == frozenset({"History"})

    chromium_docs = extract_documents(history, "")
    assert len(chromium_docs) == 3
    assert chromium_docs[0].extra_metadata["browser"] == "chromium"

    firefox_docs = extract_documents(places, "")
    assert len(firefox_docs) == 1
    assert firefox_docs[0].extra_metadata["browser"] == "firefox"

    assert discover_files(tmp_path) == sorted([history, places])
