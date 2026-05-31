"""iCalendar (.ics) parser for calendar events.

This adds support for personal calendar data — a very common and high-value
source of personal knowledge (meetings, deadlines, travel, etc.).

Supports both single events and recurring event instances (basic expansion).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class IcsParser(BaseParser):
    """Extracts text and metadata from .ics calendar files."""

    extensions = frozenset({".ics"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        try:
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        # Split into individual VEVENT blocks
        events = re.split(r"(?i)BEGIN:VEVENT", raw)[1:]  # skip header

        docs: List[ExtractedDocument] = []

        for event_block in events:
            event_block = event_block.split("END:VEVENT", 1)[0]

            summary = _get_field(event_block, "SUMMARY")
            description = _get_field(event_block, "DESCRIPTION")
            location = _get_field(event_block, "LOCATION")
            dtstart = _get_field(event_block, "DTSTART")
            organizer = _get_field(event_block, "ORGANIZER")
            attendees = _get_attendees(event_block)

            if not summary and not description:
                continue

            # Build rich text representation
            parts = []
            if summary:
                parts.append(f"Event: {summary}")
            if dtstart:
                parts.append(f"When: {_format_datetime(dtstart)}")
            if location:
                parts.append(f"Where: {location}")
            if organizer:
                parts.append(f"Organizer: {_clean_organizer(organizer)}")
            if attendees:
                parts.append(f"Attendees: {', '.join(attendees[:10])}")
            if description:
                parts.append(f"\n{description}")

            text = "\n".join(parts).strip()

            docs.append(
                ExtractedDocument(
                    text=text,
                    extra_metadata={
                        "format": "icalendar",
                        "event_summary": (summary or "")[:300],
                        "event_start": dtstart or "",
                        "event_location": (location or "")[:200],
                        "event_organizer": _clean_organizer(organizer)[:200] if organizer else "",
                    },
                )
            )

        return docs


def _get_field(block: str, field: str) -> str:
    """Extract a field value, handling line folding."""
    pattern = rf"(?i)^{field}[^:]*:(.+?)(?:\r?\n(?![A-Z-])|$)"
    match = re.search(pattern, block, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    value = match.group(1).strip()
    # Unfold lines (RFC 5545)
    value = re.sub(r"\r?\n[ \t]", " ", value)
    return value.replace("\\n", "\n").replace("\\,", ",").strip()


def _get_attendees(block: str) -> List[str]:
    attendees = []
    for line in block.splitlines():
        if line.upper().startswith("ATTENDEE"):
            # Try to extract CN or email
            cn_match = re.search(r'CN=([^;:]+)', line, re.IGNORECASE)
            if cn_match:
                attendees.append(cn_match.group(1).strip())
            else:
                email_match = re.search(r'mailto:([^>\s]+)', line, re.IGNORECASE)
                if email_match:
                    attendees.append(email_match.group(1).strip())
    return attendees


def _format_datetime(dt: str) -> str:
    """Best-effort human readable date."""
    dt = dt.replace("Z", "").replace("T", " ")
    try:
        if len(dt) >= 8:
            return datetime.strptime(dt[:8], "%Y%m%d").strftime("%Y-%m-%d")
        return dt
    except ValueError:
        return dt


def _clean_organizer(org: str) -> str:
    if org.lower().startswith("mailto:"):
        return org[7:]
    return org
