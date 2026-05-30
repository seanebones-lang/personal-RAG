"""RFC822 .eml email parser."""

from __future__ import annotations

import email
from email import policy
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class EmlParser(BaseParser):
    extensions = frozenset({".eml"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        with open(file_path, "rb") as fh:
            msg = email.message_from_binary_file(fh, policy=policy.default)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    payload = part.get_content()
                    if isinstance(payload, str):
                        body = payload
                        break
        else:
            payload = msg.get_content()
            if isinstance(payload, str):
                body = payload

        subject = str(msg.get("subject", ""))
        from_addr = str(msg.get("from", ""))
        date_hdr = str(msg.get("date", ""))

        header_block = f"Subject: {subject}\nFrom: {from_addr}\nDate: {date_hdr}\n\n"
        text = (header_block + body).strip()
        if not text:
            return []

        return [
            ExtractedDocument(
                text=text,
                extra_metadata={
                    "format": "eml",
                    "message_from": from_addr[:200],
                    "message_subject": subject[:200],
                    "message_date": date_hdr[:80],
                },
            )
        ]
