"""Browser bookmark parsers.

Currently supports:
- Chrome / Edge / Brave HTML bookmark exports (the most common format)
- Basic support for nested folder structure

Planned / future:
- Raindrop.io JSON export
- Pinboard JSON export
- Generic bookmark JSON

The parser extracts:
- Title
- URL
- Date added (when available)
- Folder path (preserving hierarchy)
- Tags (if present in the export)
"""

from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class ChromeBookmarksHTMLParser(HTMLParser):
    """Parser for Chrome/Edge/Brave bookmark HTML exports."""

    def __init__(self):
        super().__init__()
        self.docs: List[ExtractedDocument] = []
        self.current_folder_path: List[str] = []
        self.in_dt = False
        self.current_href: Optional[str] = None
        self.current_title: List[str] = []
        self.current_add_date: Optional[str] = None
        self.current_tags: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        attrs_dict = dict(attrs)

        if tag == "h3":
            # Folder name
            self.current_title = []
            self.in_dt = False

        elif tag == "a":
            self.in_dt = True
            self.current_href = attrs_dict.get("href", "")
            self.current_add_date = attrs_dict.get("add_date")
            self.current_tags = attrs_dict.get("tags")
            self.current_title = []

        elif tag == "dl":
            # Entering a new folder level
            pass

    def handle_endtag(self, tag: str):
        if tag == "h3":
            # Finished reading a folder name
            folder_name = "".join(self.current_title).strip()
            if folder_name:
                self.current_folder_path.append(folder_name)
            self.current_title = []

        elif tag == "a":
            self.in_dt = False
            title = "".join(self.current_title).strip()
            url = self.current_href or ""

            if url and title:
                self._add_bookmark(title, url)

            # Reset
            self.current_href = None
            self.current_add_date = None
            self.current_tags = None
            self.current_title = []

        elif tag == "dl":
            # Exiting a folder
            if self.current_folder_path:
                self.current_folder_path.pop()

    def handle_data(self, data: str):
        if self.in_dt or (self.current_title is not None):
            self.current_title.append(data)

    def _add_bookmark(self, title: str, url: str):
        folder_path = " / ".join(self.current_folder_path) if self.current_folder_path else "Root"

        # Format date if available
        date_str = ""
        if self.current_add_date:
            try:
                ts = int(self.current_add_date)
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                date_str = self.current_add_date

        text = f"Bookmark: {title}\nURL: {url}"
        if folder_path and folder_path != "Root":
            text += f"\nFolder: {folder_path}"
        if date_str:
            text += f"\nAdded: {date_str}"

        extra = {
            "format": "browser_bookmark",
            "title": title[:500],
            "url": url,
            "folder": folder_path[:500],
            "date_added": date_str,
        }

        if self.current_tags:
            extra["tags"] = self.current_tags[:300]

        self.docs.append(ExtractedDocument(text=text, extra_metadata=extra))


class BookmarksHTMLParser(BaseParser):
    """Parser for Chrome/Edge/Brave bookmark HTML exports."""

    extensions = frozenset({".html", ".htm"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        # Heuristic: only try to parse files that look like bookmark exports
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        # Quick check for Chrome bookmark export signature
        if "Bookmarks" not in content and "PERSONAL_TOOLBAR_FOLDER" not in content:
            # Not a bookmark export, let the generic HTML parser handle it
            return []

        parser = ChromeBookmarksHTMLParser()
        try:
            parser.feed(content)
        except Exception:
            return []

        return parser.docs


# Note: We also register for common bookmark file names even if extension is .html
# The registry will call us, and we do a content check inside.
