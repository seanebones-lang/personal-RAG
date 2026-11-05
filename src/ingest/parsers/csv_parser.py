"""Structured CSV (.csv) parser — one document per row, headers as context.

Backlog Wave 8 ("HTML main-content + CSV structure parsers"): until now a
.csv file fell through the registry to the plain-text fallback, so a table
was chunked as an undifferentiated character stream — a chunk could start
mid-row, carry values with no column names, and split a single record
across two chunks. Retrieval over that text answers "which row has
value X" poorly, because the value's meaning lives in the header row
that may be thousands of characters away.

This parser gives every data row its own ExtractedDocument whose text is
the row rendered as ``Header: value`` lines, so each chunk is a complete,
self-describing record. The pipeline already suffixes multi-document
sources (``file.csv#doc3``) and passes parser metadata through, so rows
stay individually citable.

Deliberate limits (this parser declines rather than guesses):
- Fewer than two detected columns -> returns [] so single-column lists
  keep the existing plain-text behaviour.
- Dialect comes from csv.Sniffer on a sample, falling back to Excel
  (comma) format. Header presence is Sniffer's judgement, with one
  correction: Sniffer calls small sparse tables headerless, so when it
  says "no header" but the first row is entirely non-empty, non-numeric
  text, the first row is treated as the header (the spreadsheet
  convention). Genuinely headerless files — a numeric first row is the
  tell — get synthesized ``column_1..N`` names and keep every row.
- Caps: at most MAX_ROWS documents per file and MAX_CELL_CHARS per cell,
  so a pathological export cannot flood the vault with chunks.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument

logger = logging.getLogger(__name__)

MAX_ROWS = 10_000
MAX_CELL_CHARS = 2_000
_SAMPLE_CHARS = 8_192


class CsvParser(BaseParser):
    """Extracts one document per data row from a .csv file."""

    extensions = frozenset({".csv"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        try:
            raw = file_path.read_bytes()
        except OSError:
            return []
        # utf-8-sig strips the BOM Excel exports carry; errors="ignore"
        # matches the other parsers' tolerance for stray bytes.
        text = raw.decode("utf-8-sig", errors="ignore")
        if not text.strip():
            return []

        dialect, sniffer_has_header = self._sniff(text)
        try:
            rows = [
                row
                for row in csv.reader(io.StringIO(text), dialect)
                if any(cell.strip() for cell in row)
            ]
        except csv.Error as exc:
            logger.warning("CSV parse failed for %s: %s", file_path, exc)
            return []
        if not rows:
            return []
        has_header = sniffer_has_header or self._looks_like_header(rows)

        if has_header:
            headers = self._normalize_headers(rows[0])
            data_rows = rows[1:]
        else:
            headers = [f"column_{i + 1}" for i in range(len(rows[0]))]
            data_rows = rows

        if len(headers) < 2:
            return []

        docs: List[ExtractedDocument] = []
        columns_meta = "|".join(headers)[:300]
        for row_number, row in enumerate(data_rows[:MAX_ROWS], start=1):
            lines = []
            for col_idx, header in enumerate(headers):
                value = row[col_idx].strip() if col_idx < len(row) else ""
                if value:
                    lines.append(f"{header}: {value[:MAX_CELL_CHARS]}")
            if not lines:
                continue
            docs.append(
                ExtractedDocument(
                    text="\n".join(lines),
                    extra_metadata={
                        "format": "csv",
                        "row_number": row_number,
                        "columns": columns_meta,
                    },
                )
            )
        return docs

    @staticmethod
    def _sniff(text: str):
        """Best-effort dialect + header detection; Excel defaults on doubt."""
        sample = text[:_SAMPLE_CHARS]
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        try:
            has_header = sniffer.has_header(sample)
        except csv.Error:
            has_header = True
        return dialect, has_header

    @staticmethod
    def _looks_like_header(rows: List[List[str]]) -> bool:
        """Fallback header test for tables too small/sparse for Sniffer.

        A first row of entirely non-empty, non-numeric text over further
        rows reads as labels, not data (the spreadsheet convention). A
        numeric first cell is the tell of a genuinely headerless file.
        """
        if len(rows) < 2 or not rows[0]:
            return False
        for cell in rows[0]:
            value = cell.strip()
            if not value:
                return False
            try:
                float(value)
                return False
            except ValueError:
                continue
        return True

    @staticmethod
    def _normalize_headers(header_row: List[str]) -> List[str]:
        """Trim header names; fill blanks and disambiguate duplicates."""
        headers: List[str] = []
        seen: dict = {}
        for idx, raw_name in enumerate(header_row):
            name = (raw_name or "").strip() or f"column_{idx + 1}"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 1
            headers.append(name)
        return headers
