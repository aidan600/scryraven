"""AG-BLOCKED-FAP-SAFE-TERMINAL-OUTCOME-01 focused regressions."""

from __future__ import annotations

import json
from typing import Any

import pytest

from core.final_answer_packet_runtime import (
    BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE,
    BLOCKED_FAP_TERMINAL_SCHEMA_VERSION,
    BLOCKED_FAP_TERMINAL_TRACE_KEY,
    build_blocked_fap_terminal_report,
    build_blocked_fap_terminal_trace_fragment,
    build_safe_blocked_fap_summary,
)
from core.pipeline_orchestrator import PipelineError
from core.run_config import RunOutcome


def _sample_blocked_summary(
    *,
    sufficiency_decision: str = "partial_answer_authorized",
    final_answer_posture: str = "partial_answer",
) -> dict[str, Any]:
    return {
        "schema_version": "blocked_final_answer_packet_safe_summary_v1",
        "blocked_fap": True,
        "status": "blocked",
        "readiness_status": "blocked",
        "readiness_reasons": [
            "required_obligations_missing",
            "component_readiness_not_satisfied",
            "missing_required_component_coverage",
            "semantic_direct_answer_blocked",
            "final_answer_not_allowed",
        ],
        "author_input_deferred": True,
        "blocked_before_author_input": True,
        "final_answer_allowed": False,
        "final_answer_posture": final_answer_posture,
        "sufficiency_decision": sufficiency_decision,
        "missing_source_obligation_count": 7,
        "partial_source_obligation_count": 0,
        "satisfied_source_obligation_count": 2,
        "source_bound_numeric_unknown_count": 0,
        "claim_postures": ["insufficient_evidence"],
        "component_blocked_summary": {
            "schema_version": "blocked_fap_component_summary_v1",
            "component_summary_available": True,
            "expected_component_count": 2,
            "missing_component_count": 1,
            "supported_component_count": 1,
            "hard_block_candidate": True,
            "components": [
                {"status": "supported"},
                {
                    "status": "missing",
                    "blocker_reason_codes": ["missing_required_component_coverage"],
                },
            ],
        },
    }


def test_blocked_terminal_report_is_sanitized_and_non_author() -> None:
    summary = _sample_blocked_summary()
    summary["raw_prompt"] = "SECRET_PROMPT"
    summary["provider_payload"] = {"secret": True}
    report = build_blocked_fap_terminal_report(summary)

    assert "ScryRaven could not produce a supported answer." in report
    assert "Author was not invoked" in report
    assert "missing_required_component_coverage" in report
    assert "SECRET_PROMPT" not in report
    assert "provider_payload" not in report
    assert "SECRET" not in report
    assert "[[1]](" not in report


def test_blocked_terminal_trace_exports_blocked_not_partial() -> None:
    summary = _sample_blocked_summary(
        sufficiency_decision="partial_answer_authorized",
        final_answer_posture="partial_answer",
    )
    fragment = build_blocked_fap_terminal_trace_fragment(summary)
    terminal = fragment[BLOCKED_FAP_TERMINAL_TRACE_KEY]

    assert terminal["schema_version"] == BLOCKED_FAP_TERMINAL_SCHEMA_VERSION
    assert terminal["exported_terminal_posture"] == BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE
    assert terminal["exported_terminal_posture"] == "blocked"
    assert terminal["answer_class"] == "no_evidence_found"
    assert terminal["response_displayable"] is False
    assert terminal["evidence_sufficient"] is False
    assert terminal["author_called"] is False
    assert terminal["author_payload_derived"] is False
    assert terminal["partial_candidate_not_fap_safe"] is True
    assert terminal["sufficiency_decision_lineage"] == "partial_answer_authorized"
    assert terminal["blocked_fap_summary"]["sufficiency_decision"] == (
        "partial_answer_authorized"
    )


def test_safe_summary_empty_when_authority_not_blocked() -> None:
    assert build_safe_blocked_fap_summary({"status": "ready"}) == {}
    assert build_safe_blocked_fap_summary(None) == {}


def test_pipeline_error_still_exists_for_non_blocked_invariant_failures() -> None:
    with pytest.raises(PipelineError, match="FinalAnswerPacket did not produce Author input"):
        raise PipelineError("FinalAnswerPacket did not produce Author input")


def test_run_outcome_shape_accepts_blocked_terminal_fields() -> None:
    outcome = RunOutcome(
        session_id="s",
        run_id="r",
        session_title="t",
        query="q",
        core_topic="c",
        report=build_blocked_fap_terminal_report(_sample_blocked_summary()),
        top_passages=[],
        seen_urls=[],
        collected_images=[],
        execution_trace=build_blocked_fap_terminal_trace_fragment(
            _sample_blocked_summary()
        ),
        failure_card={
            "show": True,
            "reason": "blocked_final_answer_packet",
            "blocked_fap": True,
            "exported_terminal_posture": "blocked",
            "author_called": False,
        },
        new_session={},
        cost_snapshot={},
        latency_seconds=0.0,
        intent="general",
        complexity="simple",
        corpus_state="ok",
        pipeline_config={},
        terminal_status="blocked",
        author_streamed=False,
    )
    assert isinstance(outcome, RunOutcome)
    assert outcome.terminal_status == "blocked"
    assert outcome.failure_card["author_called"] is False
    assert outcome.execution_trace[BLOCKED_FAP_TERMINAL_TRACE_KEY][
        "exported_terminal_posture"
    ] == "blocked"
    rendered = json.dumps(outcome.failure_card, sort_keys=True)
    assert "raw_prompt" not in rendered
