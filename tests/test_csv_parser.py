"""Tests for the structured CSV parser (Backlog Wave 8)."""

from pathlib import Path

import pytest

from src.ingest.parsers.csv_parser import CsvParser
from src.ingest.parsers.registry import extract_documents


@pytest.fixture
def csv_path():
    return Path(__file__).parent / "fixtures" / "sample.csv"


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_one_document_per_row_with_header_context(csv_path):
    docs = CsvParser().extract(csv_path)

    assert len(docs) == 3
    first = docs[0]
    assert "Title: The Left Hand of Darkness" in first.text
    assert "Author: Ursula K. Le Guin" in first.text
    assert "Year: 1969" in first.text
    assert first.extra_metadata["format"] == "csv"
    assert first.extra_metadata["row_number"] == 1
    assert "Title" in first.extra_metadata["columns"]
    assert docs[2].extra_metadata["row_number"] == 3


def test_quoted_commas_stay_inside_the_cell(tmp_path):
    path = _write(tmp_path, "q.csv", 'Name,Note\n"Smith, John","Paid, in full"\n')
    docs = CsvParser().extract(path)

    assert len(docs) == 1
    assert "Name: Smith, John" in docs[0].text
    assert "Note: Paid, in full" in docs[0].text


def test_semicolon_dialect_is_sniffed(tmp_path):
    path = _write(tmp_path, "s.csv", "City;Temp\nCleburne;91\nMansfield;90\n")
    docs = CsvParser().extract(path)

    assert len(docs) == 2
    assert "City: Cleburne" in docs[0].text
    assert "Temp: 91" in docs[0].text


def test_headerless_file_gets_synthesized_columns(tmp_path):
    path = _write(tmp_path, "h.csv", "10,20,30\n40,50,60\n")
    docs = CsvParser().extract(path)

    assert len(docs) == 2
    assert "column_1: 10" in docs[0].text
    assert "column_3: 60" in docs[1].text


def test_single_column_file_declines_to_fallback(tmp_path):
    path = _write(tmp_path, "list.csv", "just\nsome\nwords\n")
    assert CsvParser().extract(path) == []


def test_empty_cells_are_omitted_and_blank_rows_skipped(tmp_path):
    path = _write(tmp_path, "e.csv", "A,B,C\n1,,3\n,,\n4,5,\n")
    docs = CsvParser().extract(path)

    assert len(docs) == 2
    assert "B:" not in docs[0].text
    assert "A: 4" in docs[1].text


def test_duplicate_and_blank_headers_are_disambiguated(tmp_path):
    path = _write(tmp_path, "d.csv", "Name,,Name\nx,1,y\n")
    docs = CsvParser().extract(path)

    assert len(docs) == 1
    assert "Name: x" in docs[0].text
    assert "column_2: 1" in docs[0].text
    assert "Name_2: y" in docs[0].text


def test_bom_from_excel_exports_is_tolerated(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbfA,B\n1,2\n")
    docs = CsvParser().extract(path)

    assert len(docs) == 1
    assert "A: 1" in docs[0].text


def test_registry_routes_csv_through_the_parser(csv_path):
    docs = extract_documents(csv_path, fallback_text="Title,Author,Year,Rating")

    assert len(docs) == 3
    assert docs[0].extra_metadata["format"] == "csv"
