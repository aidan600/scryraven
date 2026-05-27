"""Sprint 4: regression guards for follow-up output shape (tables, numerics, mode)."""

from __future__ import annotations

import re

from core.followup import (
    MemorySearchResult,
    WebRetrievalResult,
    complexity_for_ui_mode,
    resolve_followup_mode,
    run_followup_synthesis,
)
from core.output_validation import enforce_table_width, max_table_cols


def test_followup_output_wide_table_enforced_to_max_four_cols() -> None:
    six_col_markdown = (
        "| Aircraft | CASM ¢ | Stage length | Year | Hub | Notes |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| MD-83 | 12 | 800 mi | 2019 | DFW | legacy |\n"
    )

    def model_fn(_prompt: str) -> str:
        return six_col_markdown

    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=[],
        existing_evidence_block="",
        needs_search=False,
        followup_queries=[],
    )
    web = WebRetrievalResult(
        sources={},
        next_source_id=1,
        new_passages=[],
        new_evidence_block="",
        seen_urls=[],
        collected_images=[],
    )
    result = run_followup_synthesis(
        query="Compare aircraft economics",
        memory_result=memory,
        web_result=web,
        session={"report": ""},
        current_date="2026-04-01",
        follow_complexity="medium",
        image_context="",
        is_plausible_domain=lambda _u: True,
        model_fn=model_fn,
    )
    assert max_table_cols(result.answer) <= 4


def test_followup_output_no_wide_tables_direct_enforce() -> None:
    """Explicit guard: enforce_table_width collapses model violations."""
    wide = "| c1 | c2 | c3 | c4 | c5 | c6 |\n|---|---|---|---|---|---|\n| v | v | v | v | v | v |\n"
    fixed = enforce_table_width(wide, max_cols=4)
    assert max_table_cols(fixed) <= 4


def test_casm_synthesis_contains_numeric_figure() -> None:
    realistic = (
        "Route-level **unit costs** for comparable stage lengths were typically **10–14¢** "
        "per ASM for narrowbody fleets in that era; one analyst cited **6.8** ¢ on shorter hops.\n"
    )

    def model_fn(_p: str) -> str:
        return realistic

    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=[],
        existing_evidence_block="",
        needs_search=False,
        followup_queries=[],
    )
    web = WebRetrievalResult(
        sources={},
        next_source_id=1,
        new_passages=[],
        new_evidence_block="",
        seen_urls=[],
        collected_images=[],
    )
    result = run_followup_synthesis(
        query="What were typical CASM figures?",
        memory_result=memory,
        web_result=web,
        session={"report": "Airline cost excerpt."},
        current_date="2026-04-01",
        follow_complexity="medium",
        image_context="",
        is_plausible_domain=lambda _u: True,
        model_fn=model_fn,
    )
    assert re.search(r"\d+[\-–]\d+", result.answer)
    assert re.search(r"\d+\.?\d*", result.answer)


def test_followup_mode_never_escalates_above_parent_fast_balanced() -> None:
    for parent_mode in ("Fast", "Balanced"):
        session = {"last_report_mode": parent_mode}
        resolved = resolve_followup_mode(session)
        assert resolved == parent_mode
        assert complexity_for_ui_mode(resolved) != "high"
