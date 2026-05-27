"""Tests for ``analyst_thin_quant`` DATA_UNAVAILABLE parsing (``core/pipeline.py``)."""

from __future__ import annotations

from core.pipeline import parse_thin_quant_data_unavailable, thin_quant_preflight_missing_entities


def test_parse_data_unavailable_json_array() -> None:
    text = 'DATA_UNAVAILABLE: ["DOT Form 41 Schedule P1.2", "SEC 10-K filings"]'
    ok, items = parse_thin_quant_data_unavailable(text)
    assert ok is True
    assert items == ["DOT Form 41 Schedule P1.2", "SEC 10-K filings"]


def test_parse_data_unavailable_comma_separated() -> None:
    text = "DATA_UNAVAILABLE: DOT Form 41 Schedule P1.2 CASM, MIT Airline Data Project"
    ok, items = parse_thin_quant_data_unavailable(text)
    assert ok is True
    assert len(items) == 2
    assert "MIT Airline Data Project" in items


def test_parse_data_unavailable_not_triggered() -> None:
    ok, items = parse_thin_quant_data_unavailable("- anchored claim — Source 1")
    assert ok is False
    assert items == []


def test_parse_data_unavailable_empty_payload() -> None:
    ok, items = parse_thin_quant_data_unavailable("DATA_UNAVAILABLE:")
    assert ok is True
    assert items == []


def test_preflight_missing_entities_all_true() -> None:
    assert thin_quant_preflight_missing_entities(
        {"A": True, "B": True}, ["A", "B"]
    ) == []


def test_preflight_missing_entities_case_insensitive_keys() -> None:
    assert thin_quant_preflight_missing_entities(
        {"boeing 777": True}, ["Boeing 777"]
    ) == []


def test_preflight_missing_entities_false_or_absent() -> None:
    assert thin_quant_preflight_missing_entities(
        {"MD-80": True, "777-300": False}, ["MD-80", "777-300"]
    ) == ["777-300"]
    assert thin_quant_preflight_missing_entities(
        {"MD-80": True}, ["MD-80", "777-300"]
    ) == ["777-300"]
