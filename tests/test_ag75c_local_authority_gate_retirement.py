from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_OWNER,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
    PROVIDER_SEARCH_REVIEW_REQUEST,
)
from core.recovered_evidence_visibility import (
    apply_controller_recovered_evidence_visibility,
    apply_recovered_evidence_visibility_boundary,
    recovered_evidence_selection_candidates,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_VISIBILITY_PATH = _ROOT / "core" / "recovered_evidence_visibility.py"


def _official_source(**overrides: Any) -> dict[str, Any]:
    source = {
        "source_id": "official-current-rule",
        "title": "Official current rule",
        "url": "https://agency.gov/current-rule",
        "text": "The agency current rule is in force for 2026.",
        "score": 0.87,
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "retrieval_stage": "source_class_recovery",
    }
    source.update(overrides)
    return source


def _context_source() -> dict[str, Any]:
    return {
        "title": "Context analysis",
        "url": "https://analysis.example/context",
        "text": "Background analysis.",
        "score": 0.99,
        "source_tier": "secondary",
        "source_class": "secondary",
    }


def _controller_trace(
    allocation_result: dict[str, Any] | None = None,
    *,
    authorized: bool = True,
) -> dict[str, Any]:
    owner = PROVIDER_SEARCH_ALLOCATION_OWNER if authorized else "local_orchestrator_state"
    return {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": "answer_contract_official_gap_missing",
        "authority_lifecycle": {
            "execution_state": {"state": "attempted", "result_count": 1},
            "recovery_action": {
                "action_type": "recover_missing_source_class",
                "approved": True,
                "required_source_classes": ["official_current_rules"],
                "provider_role": "source_class_recovery",
            },
        },
        PROVIDER_SEARCH_ALLOCATION_TRACE_KEY: {
            PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: {
                "allocation_owner": owner,
                "authorized_decision": (
                    PROVIDER_SEARCH_REVIEW_REQUEST if authorized else "continue_downstream"
                ),
                "authorized_executor_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
                "bounded_profile": BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
                "executed": allocation_result is not None,
                "execution_attempted": allocation_result is not None,
                "result_count": 1 if allocation_result is not None else 0,
                "new_url_count": 1 if allocation_result is not None else 0,
                "allocation_result_summaries": (
                    [allocation_result] if allocation_result is not None else []
                ),
            }
        },
    }


def test_ag75c_controller_visibility_helper_matches_existing_boundary() -> None:
    trace = _controller_trace()
    all_passages = [_context_source(), _official_source()]
    candidates = recovered_evidence_selection_candidates(
        all_passages=all_passages,
        lifecycle_trace=trace,
    )
    expected_trace = deepcopy(trace)

    expected, expected_decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_context_source()],
        recovered_passages=candidates,
        lifecycle_trace=expected_trace,
        max_final_evidence=2,
        reserve_limit=1,
    )
    actual = apply_controller_recovered_evidence_visibility(
        final_top_evidence=[_context_source()],
        all_passages=all_passages,
        lifecycle_trace=trace,
        max_final_evidence=2,
        reserve_limit=1,
    )

    assert [source["url"] for source in actual] == [
        source["url"] for source in expected
    ]
    assert trace["recovered_visibility_source_fit_status"] == (
        expected_decision.source_fit_status
    )
    assert trace["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "matched_selected"
    )


def test_ag75c_allocation_candidate_pool_is_controller_custody_owned() -> None:
    allocation_result = _official_source(
        source_url="https://agency.gov/allocation-rule",
        url="https://agency.gov/allocation-rule",
        provider_result_id="provider-result-1",
        candidate_id="candidate-1",
        retrieval_stage="provider_search_allocation",
    )
    authorized_trace = _controller_trace(allocation_result, authorized=True)
    unauthorized_trace = _controller_trace(allocation_result, authorized=False)

    authorized = recovered_evidence_selection_candidates(
        all_passages=[],
        lifecycle_trace=authorized_trace,
    )
    unauthorized = recovered_evidence_selection_candidates(
        all_passages=[],
        lifecycle_trace=unauthorized_trace,
    )

    assert [source["url"] for source in authorized] == [
        "https://agency.gov/allocation-rule"
    ]
    assert unauthorized == []


def test_ag75c_pipeline_orchestrator_no_longer_owns_recovered_pool_gate() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "def _apply_recovered_evidence_visibility" not in orchestrator_source
    assert "allocation_result_candidates_for_existing_selection_corridor" not in (
        orchestrator_source
    )
    assert "apply_recovered_evidence_visibility_boundary(" not in orchestrator_source
    assert "recovered_evidence_visibility=apply_controller_recovered_evidence_visibility" in (
        orchestrator_source
    )
    assert "build_final_evidence_runtime_handoff_from_scope(" in orchestrator_source
    assert "build_final_evidence_bundle(" not in orchestrator_source


def test_ag75c_visibility_handoff_keeps_protected_surfaces_closed() -> None:
    helper_source = _VISIBILITY_PATH.read_text(encoding="utf-8").casefold()

    assert "select_providers(" not in helper_source
    assert "process_search_queries(" not in helper_source
    assert "ask_model(" not in helper_source
    assert "build_final_answer(" not in helper_source
    assert "linkup_depth_override" not in helper_source
