"""EPUB parser tests (stdlib fallback path)."""

import zipfile
from pathlib import Path

from src.ingest.parsers.epub import EpubParser


def _write_minimal_epub(path: Path, body: str) -> None:
    """Write a barebones EPUB zip with one xhtml chapter."""
    container = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test Book</dc:title>
    <dc:identifier id="id">test-id</dc:identifier>
  </metadata>
  <manifest>
    <item id="c1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="c1"/>
  </spine>
</package>
"""
    xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>{body}</p></body></html>
"""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/chap1.xhtml", xhtml)


def test_epub_fallback_extract(tmp_path):
    epub = tmp_path / "book.epub"
    _write_minimal_epub(epub, "Hello from the personal vault chapter.")
    docs = EpubParser().extract(epub)
    assert len(docs) == 1
    assert "Hello from the personal vault" in docs[0].text
    assert docs[0].extra_metadata.get("format") == "epub"
