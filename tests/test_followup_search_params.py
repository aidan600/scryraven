"""Tests for follow-up search tier mapping (Phase 1)."""

from core.pipeline import get_followup_search_params


def test_followup_low_tier() -> None:
    p = get_followup_search_params("low", "basic")
    assert p["search_depth"] == "basic"
    assert p["max_results"] == 6
    assert p["top_passage_count"] == 8
    assert p["max_queries"] == 2
    assert p["linkup_depth_override"] is None


def test_followup_medium_uses_advanced_when_stored_basic() -> None:
    p = get_followup_search_params("medium", "basic")
    assert p["search_depth"] == "advanced"
    assert p["max_results"] == 6
    assert p["top_passage_count"] == 12
    assert p["max_queries"] == 3


def test_followup_high_tier() -> None:
    p = get_followup_search_params("high", "advanced")
    assert p["search_depth"] == "advanced"
    assert p["max_results"] == 8
    assert p["top_passage_count"] == 16
    assert p["max_queries"] == 4
    assert p["linkup_depth_override"] == "deep"
