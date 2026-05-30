import pytest

from src.filters import build_where


def test_build_where_year():
    w = build_where(where_year=2025)
    assert w == {"year": 2025}


def test_build_where_and():
    w = build_where(where_year=2025, extension="pdf")
    assert w == {"$and": [{"year": 2025}, {"extension": ".pdf"}]}


def test_build_where_invalid_json():
    with pytest.raises(ValueError, match="JSON"):
        build_where(filter_json="not-json")
