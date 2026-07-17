"""Inert compatibility exports for the retired legacy semantic Scout."""

from __future__ import annotations

from typing import Any

QUANT_REPORT_TYPES = {
    "quantitative_comparison",
    "cost_analysis",
    "financial_model",
    "unit_economics",
    "benchmark",
}


def run_scout(*_args: Any, **_kwargs: Any) -> None:
    """Return the fixed retired result without prompt lookup or model execution."""

    return None


def should_skip_quant_scout(*_args: Any, **_kwargs: Any) -> bool:
    """Keep legacy validation composition inert after Scout retirement."""

    return True
