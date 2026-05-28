from __future__ import annotations

from pathlib import Path
from typing import Any

from core.allocation_candidate_selection_activation import (
    allocation_result_candidates_for_existing_selection_corridor,
)
from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import REQUEST_PROVIDER_SEARCH_REVIEW
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.runtime_trace_projection_assembly import attach_passive_runtime_projection_traces
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_HELPER_PATH = _ROOT / "core" / "allocation_candidate_selection_activation.py"
_CUSTODY_PATH = _ROOT / "core" / "allocation_result_candidate_custody.py"
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"


def _allocation_execution_trace(
    result: dict[str, Any],
    *,
    authorized: bool = True,
    executed: bool = True,
    admitted: bool = True,
) -> dict[str, Any]:
    owner = "ControllerRecoveryDecision" if authorized else "local_orchestrator_state"
    return {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": (
            "official_canonical_recovery_query_acquisition_gap"
        ),
        "source_survival_final_evidence_official_or_canonical_count": 0,
        "source_survival_final_citation_official_or_canonical_count": 0,
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
                    REQUEST_PROVIDER_SEARCH_REVIEW if authorized else "continue_downstream"
                ),
                "authorized_executor_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
                "bounded_profile": BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
                "executed": executed,
                "execution_attempted": executed,
                "result_count": 1 if admitted else 0,
                "new_url_count": 1 if admitted else 0,
                "allocation_result_summaries": [result] if admitted else [],
            }
        },
    }


def _official_result(**overrides: Any) -> dict[str, Any]:
    result = {
        "title": "Official current rule",
        "url": "https://agency.gov/current-rule",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "classification_reason": "declared_source_class",
    }
    result.update(overrides)
    return result


def test_ag75a_z_allocation_candidate_enters_existing_selection_corridor() -> None:
    trace = _allocation_execution_trace(_official_result())
    recovered = allocation_result_candidates_for_existing_selection_corridor(trace)

    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=recovered,
        lifecycle_trace=trace,
        max_final_evidence=4,
        reserve_limit=1,
    )

    assert [source["url"] for source in recovered] == [
        "https://agency.gov/current-rule"
    ]
    assert decision.source_fit_status == "matched_selected"
    assert decision.source_fit_selected_count == 1
    assert [source["url"] for source in final] == ["https://agency.gov/current-rule"]

    projected = attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=recovered,
        final_top_evidence=final,
        surface_visibility={
            "controller_visible_urls": ["https://agency.gov/current-rule"],
            "answer_contract_visible_urls": ["https://agency.gov/current-rule"],
            "context_packet_visible_urls": ["https://agency.gov/current-rule"],
            "analyst_visible_urls": ["https://agency.gov/current-rule"],
            "author_visible_urls": ["https://agency.gov/current-rule"],
            "cited_in_final_answer_urls": ["https://agency.gov/current-rule"],
        },
    )
    ledger = projected["controller_evidence_ledger"]["ControllerEvidenceLedger"]
    assert len(ledger["selected_evidence"]) == 1
    assert ledger["selected_evidence"][0]["event_type"] == "AuthorityEvidenceSelected"
    assert_execution_trace_payload_contract(projected)


def test_ag75a_z_controller_authorization_and_custody_are_required() -> None:
    unauthorized = _allocation_execution_trace(_official_result(), authorized=False)
    not_executed = _allocation_execution_trace(
        _official_result(),
        executed=False,
        admitted=False,
    )
    local_only = {
        "authority_lifecycle": {
            "candidate_fit": {
                "selected_authority_evidence": [
                    {"url": "https://agency.gov/current-rule"}
                ]
            }
        }
    }

    assert allocation_result_candidates_for_existing_selection_corridor(unauthorized) == []
    assert allocation_result_candidates_for_existing_selection_corridor(not_executed) == []
    assert allocation_result_candidates_for_existing_selection_corridor(local_only) == []


def test_ag75a_z_classifier_currentness_gate_is_required_before_fit() -> None:
    missing_class = _allocation_execution_trace(
        _official_result(source_class="unknown")
    )
    missing_currentness = _allocation_execution_trace(
        _official_result(currentness_signal="unknown")
    )

    assert allocation_result_candidates_for_existing_selection_corridor(missing_class) == []
    assert (
        allocation_result_candidates_for_existing_selection_corridor(
            missing_currentness
        )
        == []
    )


def test_ag75a_z_existing_fit_rules_reject_non_matching_allocation_candidate() -> None:
    trace = _allocation_execution_trace(
        _official_result(
            url="https://primary.example/current-rule",
            source_tier="primary",
            source_class="primary_source_documents",
        )
    )
    recovered = allocation_result_candidates_for_existing_selection_corridor(trace)

    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=recovered,
        lifecycle_trace=trace,
        max_final_evidence=4,
        reserve_limit=1,
    )

    assert recovered
    assert final == []
    assert decision.source_fit_status == "no_matching_source_fit"
    assert "source_class_mismatch" in decision.source_fit_rejection_reasons


def test_ag75a_z_lower_tier_candidates_never_satisfy_official_current() -> None:
    trace = _allocation_execution_trace(
        _official_result(
            url="https://example.com/forum-thread",
            source_tier="secondary",
            source_class="secondary",
        )
    )

    assert allocation_result_candidates_for_existing_selection_corridor(trace) == []


def test_ag75a_z_no_new_passive_projection_or_export_surface() -> None:
    export_source = _EXPORT_PATH.read_text(encoding="utf-8").casefold()
    assembly_source = _ASSEMBLY_PATH.read_text(encoding="utf-8").casefold()

    assert "allocation_candidate_selection_activation_available" not in export_source
    assert "allocation_candidate_selection_activation_trace_key" not in assembly_source
    assert "allocationcandidateselectionactivation" not in assembly_source


def test_ag75a_z_raw_payloads_and_protected_surfaces_stay_closed() -> None:
    trace = _allocation_execution_trace(
        _official_result(
            text="raw text must not surface",
            raw_provider_payload="secret provider payload must not surface",
        )
    )
    recovered = allocation_result_candidates_for_existing_selection_corridor(trace)
    rendered = repr(recovered).casefold()
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    custody_source = _CUSTODY_PATH.read_text(encoding="utf-8").casefold()

    assert "secret provider payload" not in rendered
    assert "raw text must not surface" not in rendered
    assert "source_classifier" not in helper_source
    assert "candidate_fit(" not in helper_source
    assert "legal_current_authority_fit" not in helper_source
    assert "build_final_answer(" not in helper_source
    assert "build_final_answer(" not in custody_source


def test_ag75a_z_pipeline_orchestrator_is_tiny_handoff_not_selection_owner() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()

    assert "allocation_result_candidates_for_existing_selection_corridor" in (
        orchestrator_source
    )
    assert "allocationcandidateselectionactivation" not in orchestrator_source
    assert "authorityevidenceselected" not in orchestrator_source
    assert "promoted_final_authority_evidence" not in orchestrator_source
    assert orchestrator_source.count("apply_recovered_evidence_visibility_boundary(") == 1
