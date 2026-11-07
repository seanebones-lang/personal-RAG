"""Browser history parser — one document per visited URL (opt-in).

Backlog Wave 8 ("Browser history opt-in parser"): the vault already
ingests browser *bookmarks* (deliberate saves, via HTML/JSON exports),
but not browser *history* — the record of what was actually visited,
which is often the faster route back to "that page I was reading last
week". This parser reads the two standard history stores:

- Chromium family (Chrome, Edge, Brave, Opera, …): the ``urls`` table
  of the profile's ``History`` SQLite file (no extension — claimed by
  exact file name via ``BaseParser.filenames``).
- Firefox: the ``moz_places`` table of ``places.sqlite`` (claimed via
  the ``.sqlite`` suffix and content-sniffed — a database without
  history tables is declined).

Opt-in is the design's spine. Browsing history is among the most
sensitive data on a machine, so the parser is registered only when the
user explicitly enables it (``PRV_INGEST_BROWSER_HISTORY``, see
``Settings.ingest_browser_history``); with the flag off the registry
never claims ``.sqlite`` files or ``History`` names and discovery
never picks them up. When it is on, the user copies a history store
into the vault like any other source file.

Safety: the store is *copied* to a temporary file and the copy is
queried. The original is never opened by SQLite, so a running
browser's lock is never contended and no journal/WAL side effects can
touch the live profile; the copy reads the last committed state.

Emission: one ExtractedDocument per visited URL (the ``urls`` /
``moz_places`` level), most recent visit first — a visited page, like
a CSV row, is one citable record. Text renders the title (falling
back to the URL when the browser recorded none — history titles are
often empty, and declining those rows would gut coverage), the URL,
the last-visit time in UTC, and the visit count. Firefox-internal
rows are skipped: ``place:`` pseudo-URLs and ``hidden`` redirect /
frame entries are browser plumbing, not visits a person made.
Chromium timestamps are microseconds since 1601; Firefox's are
microseconds since the Unix epoch.

Deliberate limits (this parser declines rather than guesses):
- A file that is not a readable SQLite database with one of the two
  history schemas -> returns [] (and the registry never falls back to
  wrapping the binary store as plain text; see registry.py).
- Per-visit timeline rows (Chromium ``visits``, Firefox
  ``moz_historyvisits``), downloads, and search terms are not
  emitted — per-URL records are the citable unit here.
- Caps: at most MAX_ENTRIES documents per store, title truncated to
  MAX_TITLE_CHARS, so a decade-old profile cannot flood the vault.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from src.ingest.parsers.base import BaseParser, ExtractedDocument

logger = logging.getLogger(__name__)

MAX_ENTRIES = 10_000
MAX_TITLE_CHARS = 500

# Chromium/WebKit epoch (1601-01-01) as a Unix timestamp offset.
_CHROMIUM_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)

# (url, title, visit_count, last_visit_microseconds)
_Row = Tuple[str, Optional[str], Optional[int], Optional[int]]


class BrowserHistoryParser(BaseParser):
    """Extracts one document per visited URL from a browser history store."""

    extensions = frozenset({".sqlite"})
    filenames = frozenset({"History"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        rows, browser = self._read_rows(file_path)
        if browser is None:
            return []

        docs: List[ExtractedDocument] = []
        for url, title, visit_count, last_visit_us in rows:
            if not url or last_visit_us is None:
                continue
            visited = self._format_timestamp(browser, last_visit_us)
            if visited is None:
                continue
            headline = (title or "").strip() or url
            lines = [f"History: {headline}"]
            lines.append(f"URL: {url}")
            lines.append(f"Visited: {visited}")
            if visit_count:
                lines.append(f"Visits: {visit_count}")
            docs.append(
                ExtractedDocument(
                    text="\n".join(lines),
                    extra_metadata={
                        "format": "browser_history",
                        "browser": browser,
                        "title": headline[:MAX_TITLE_CHARS],
                        "url": url,
                        "last_visit": visited,
                        "visit_count": int(visit_count or 0),
                    },
                )
            )
        return docs

    def _read_rows(self, file_path: Path) -> Tuple[List[_Row], Optional[str]]:
        """Copy the store to a temp file and read its history rows.

        Returns (rows, browser) where browser is "chromium" or
        "firefox"; ([], None) when the file is not a history store
        this parser understands.
        """
        try:
            with tempfile.NamedTemporaryFile(
                prefix="prv-history-", suffix=".sqlite", delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
            try:
                shutil.copyfile(file_path, tmp_path)
                return self._query_copy(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        except (OSError, sqlite3.Error) as exc:
            logger.warning("Browser history read failed for %s: %s", file_path, exc)
            return [], None

    @staticmethod
    def _query_copy(copy_path: Path) -> Tuple[List[_Row], Optional[str]]:
        conn = sqlite3.connect(f"file:{copy_path}?mode=ro", uri=True)
        try:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            if "moz_places" in tables:
                rows = conn.execute(
                    "SELECT url, title, visit_count, last_visit_date"
                    " FROM moz_places"
                    " WHERE last_visit_date IS NOT NULL"
                    " AND visit_count > 0"
                    " AND hidden = 0"
                    " AND url NOT LIKE 'place:%'"
                    " ORDER BY last_visit_date DESC"
                    " LIMIT ?",
                    (MAX_ENTRIES,),
                ).fetchall()
                return rows, "firefox"
            if "urls" in tables:
                rows = conn.execute(
                    "SELECT url, title, visit_count, last_visit_time"
                    " FROM urls"
                    " WHERE last_visit_time > 0"
                    " ORDER BY last_visit_time DESC"
                    " LIMIT ?",
                    (MAX_ENTRIES,),
                ).fetchall()
                return rows, "chromium"
            return [], None
        finally:
            conn.close()

    @staticmethod
    def _format_timestamp(browser: str, micros: int) -> Optional[str]:
        """Render a store timestamp as 'YYYY-MM-DD HH:MM' in UTC."""
        try:
            if browser == "chromium":
                moment = _CHROMIUM_EPOCH + timedelta(microseconds=micros)
            else:
                moment = datetime.fromtimestamp(micros / 1_000_000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return moment.strftime("%Y-%m-%d %H:%M")
