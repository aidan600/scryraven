"""Tier 1: deterministic entity normalization and fallback (no APIs)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.entity_extraction import fallback_entities_from_query, normalize_entities_list

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "phase_a_queries.json"


def _load_fixture() -> list[dict]:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


@pytest.mark.parametrize("case", _load_fixture(), ids=lambda c: c["id"])
def test_fallback_entities_fixture(case: dict) -> None:
    got = fallback_entities_from_query(case["query"])
    assert got == case["expected_entities"], f"id={case['id']}: got={got}"


def test_normalize_entities_list_dedupe_and_order() -> None:
    raw = ["  ASML ", "asml", "BTC", "", "BTC"]
    assert normalize_entities_list(raw) == ["ASML", "BTC"]
    assert normalize_entities_list(None) == []
    assert normalize_entities_list("x") == []
