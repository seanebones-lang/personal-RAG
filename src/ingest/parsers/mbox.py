"""Unix mbox mailbox parser."""

from __future__ import annotations

import mailbox
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class MboxParser(BaseParser):
    extensions = frozenset({".mbox"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        docs: List[ExtractedDocument] = []
        mbox = mailbox.mbox(str(file_path))
        for idx, msg in enumerate(mbox):
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and not part.get_filename():
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            body = payload.decode("utf-8", errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body = payload.decode("utf-8", errors="ignore")

            subject = str(msg.get("subject", ""))
            from_addr = str(msg.get("from", ""))
            date_hdr = str(msg.get("date", ""))
            header_block = f"Subject: {subject}\nFrom: {from_addr}\nDate: {date_hdr}\n\n"
            text = (header_block + body).strip()
            if not text:
                continue
            docs.append(
                ExtractedDocument(
                    text=text,
                    extra_metadata={
                        "format": "mbox",
                        "message_index": idx,
                        "message_from": from_addr[:200],
                        "message_subject": subject[:200],
                        "message_date": date_hdr[:80],
                    },
                )
            )
        mbox.close()
        return docs
