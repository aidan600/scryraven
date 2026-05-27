"""Economist tier budgets (complexity-aware prompts)."""

from __future__ import annotations

from core.prompts import ECONOMIST_COMPLEXITY_BUDGET, economist_budget_for_complexity


def test_economist_budget_maps_low_medium_high() -> None:
    assert "FAST" in economist_budget_for_complexity("low")
    assert "BALANCED" in economist_budget_for_complexity("medium")
    assert "DEEP" in economist_budget_for_complexity("high")


def test_economist_budget_unknown_falls_back_to_medium() -> None:
    assert economist_budget_for_complexity("unknown") == ECONOMIST_COMPLEXITY_BUDGET["medium"]
    assert economist_budget_for_complexity(None) == ECONOMIST_COMPLEXITY_BUDGET["medium"]


def test_economist_budget_no_longer_requests_python_code() -> None:
    combined = "\n".join(ECONOMIST_COMPLEXITY_BUDGET.values())
    assert "python_code" not in combined
    assert "executable Python" not in combined
