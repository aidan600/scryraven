"""Optional live checks against Tavily (integration)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.search_providers import search_web_results

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "phase_a_queries.json"


def _live_enabled() -> bool:
    return os.getenv("PROPLEX_RUN_LIVE", "").strip() == "1"


def _five_queries() -> list[str]:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return [str(item["query"]) for item in data[:5]]


requires_live = pytest.mark.skipif(
    not _live_enabled(),
    reason="Set PROPLEX_RUN_LIVE=1 to run integration smoke",
)


@pytest.mark.integration
@requires_live
def test_tavily_smoke_five_phase_a_queries() -> None:
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY not set")

    for q in _five_queries():
        results, _images = search_web_results(q, max_results=3, search_depth="basic")
        assert isinstance(results, list)
