from __future__ import annotations

from core.pipeline_orchestrator import (
    choose_retrieval_search_depth,
    choose_supplemental_search_depth,
)


def test_medium_second_iteration_uses_base_depth_by_default() -> None:
    assert choose_retrieval_search_depth("medium", "basic", iteration=2) == "basic"


def test_high_retrieval_uses_advanced_even_when_base_basic() -> None:
    assert choose_retrieval_search_depth("high", "basic", iteration=1) == "advanced"
    assert choose_retrieval_search_depth("high", "basic", iteration=2) == "advanced"


def test_low_retrieval_remains_basic() -> None:
    assert choose_retrieval_search_depth("low", "basic", iteration=1) == "basic"


def test_explicit_advanced_base_depth_is_preserved() -> None:
    assert choose_retrieval_search_depth("medium", "advanced", iteration=2) == "advanced"


def test_supplemental_medium_uses_base_depth_by_default() -> None:
    assert choose_supplemental_search_depth("medium", "basic") == "basic"


def test_supplemental_high_uses_advanced_even_when_base_basic() -> None:
    assert choose_supplemental_search_depth("high", "basic") == "advanced"


def test_explicit_escalation_reason_uses_advanced() -> None:
    assert (
        choose_retrieval_search_depth(
            "medium",
            "basic",
            iteration=2,
            explicit_escalation_reason="manual_override",
        )
        == "advanced"
    )
    assert (
        choose_supplemental_search_depth(
            "medium",
            "basic",
            explicit_escalation_reason="manual_override",
        )
        == "advanced"
    )
