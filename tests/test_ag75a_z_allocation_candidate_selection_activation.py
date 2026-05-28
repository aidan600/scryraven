from __future__ import annotations

from pathlib import Path
from typing import Any

from core.allocation_candidate_selection_activation import (
    ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_TRACE_KEY,
    build_allocation_candidate_selection_activation_projection,
)
from core.allocation_result_candidate_custody import (
    ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY,
)
from core.authority_candidate_passport import AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY
from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import REQUEST_PROVIDER_SEARCH_REVIEW
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.runtime_trace_projection_assembly import attach_passive_runtime_projection_traces
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_HELPER_PATH = _ROOT / "core" / "allocation_candidate_selection_activation.py"
_CUSTODY_PATH = _ROOT / "core" / "allocation_result_candidate_custody.py"


def _allocation_execution_trace(
    result: dict[str, Any],
    *,
    authorized: bool = True,
    executed: bool = True,
    admitted: bool = True,
) -> dict[str, Any]:
    owner = "ControllerRecoveryDecision" if authorized else "local_orchestrator_state"
    return {
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "source_survival_final_evidence_official_or_canonical_count": 0,
        "source_survival_final_citation_official_or_canonical_count": 0,
        "authority_lifecycle": {
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


def _selected_trace() -> dict[str, Any]:
    url = "https://agency.gov/current-rule"
    trace = _allocation_execution_trace(
        {
            "title": "Official current rule",
            "url": url,
            "source_tier": "official",
            "source_class": "official_current_rules",
            "currentness_signal": "current",
        }
    )
    trace["authority_lifecycle"]["candidate_fit"] = {
        "selected_authority_evidence": [
            {
                "url": url,
                "observed_source_class": "official_current_rules",
                "satisfies_authority": True,
            }
        ],
    }
    return attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[],
        final_top_evidence=[],
        surface_visibility={
            "controller_visible_urls": [url],
            "answer_contract_visible_urls": [url],
            "context_packet_visible_urls": [url],
            "analyst_visible_urls": [url],
            "author_visible_urls": [url],
            "cited_in_final_answer_urls": [url],
        },
    )


def _activation(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_TRACE_KEY][
        "AllocationCandidateSelectionActivation"
    ]


def test_ag75a_z_selected_only_through_existing_ledger_selection_corridor() -> None:
    trace = _selected_trace()

    activation = _activation(trace)
    assert activation["admitted_candidate_count"] == 1
    assert activation["eligible_for_existing_disposition_count"] == 1
    assert activation["activated_disposition_count"] == 1
    assert activation["selected_evidence_candidate_count"] == 1
    assert activation["candidate_activation_states"][0]["activation_state"] == (
        "selected_by_existing_downstream_selection_corridor"
    )
    assert activation["candidate_activation_states"][0]["selected_by_ledger"] is True
    assert activation["source_obligation_satisfied_by_allocation_result_alone"] is False
    assert activation["final_answer_behavior_changed"] is False
    assert activation["citation_behavior_changed"] is False

    passport = trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY][
        "AuthorityCandidatePassportProjection"
    ]
    ledger = trace[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY]["ControllerEvidenceLedger"]
    assert passport["passports"][0]["final_disposition"] == (
        "promoted_final_authority_evidence"
    )
    assert len(ledger["selected_evidence"]) == 1
    assert ledger["final_evidence"] == []
    assert ledger["final_citations"] == []

    export = build_official_canonical_recovery_visibility_export(trace)
    assert export["allocation_candidate_selected_evidence_candidate_count"] == 1
    assert export["allocation_candidate_final_answer_behavior_changed"] is False
    assert export["allocation_candidate_citation_behavior_changed"] is False
    assert export["final_evidence_official_or_canonical_count"] == 0
    assert export["final_citation_official_or_canonical_count"] == 0
    assert_execution_trace_payload_contract(trace)


def test_ag75a_z_controller_recovery_decision_authorization_required() -> None:
    trace = attach_passive_runtime_projection_traces(
        _allocation_execution_trace(
            {
                "url": "https://agency.gov/current-rule",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
            },
            authorized=False,
        ),
        recovered_passages=[],
        final_top_evidence=[],
    )

    custody = trace[ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY][
        "AllocationResultCandidateCustody"
    ]
    activation = _activation(trace)
    assert custody["admitted_result_count"] == 0
    assert activation["admitted_candidate_count"] == 0
    assert activation["selected_evidence_candidate_count"] == 0


def test_ag75a_z_candidate_cannot_bypass_classifier_currentness_fit_or_ledger() -> None:
    missing_currentness = attach_passive_runtime_projection_traces(
        _allocation_execution_trace(
            {
                "url": "https://agency.gov/current-rule",
                "source_tier": "official",
                "source_class": "official_current_rules",
            }
        ),
        recovered_passages=[],
        final_top_evidence=[],
    )
    assert _activation(missing_currentness)["blocked_reasons"] == [
        "missing_classifier_currentness_state"
    ]

    fit_missing = build_allocation_candidate_selection_activation_projection(
        {
            ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY: {
                "AllocationResultCandidateCustody": {
                    "allocation_execution_authorized": True,
                    "represented_candidate_inputs": [
                        {
                            "candidate_id": "allocation-result-candidate:fit-missing",
                            "url": "https://agency.gov/current-rule",
                        }
                    ],
                }
            },
            AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY: {
                "AuthorityCandidatePassportProjection": {
                    "passports": [
                        {
                            "candidate_id": "allocation-result-candidate:fit-missing",
                            "source_url": "https://agency.gov/current-rule",
                            "source_tier": "official",
                            "source_class": "official_current_rules",
                            "currentness_signal": "current",
                            "fit_state": "not_evaluated",
                            "final_disposition": "represented_without_durable_disposition",
                        }
                    ]
                }
            },
            CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY: {
                "ControllerEvidenceLedger": {"events": []}
            },
        }
    )
    assert fit_missing["blocked_reasons"] == ["missing_candidate_fit_state"]

    ledger_missing = build_allocation_candidate_selection_activation_projection(
        {
            ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY: {
                "AllocationResultCandidateCustody": {
                    "allocation_execution_authorized": True,
                    "represented_candidate_inputs": [
                        {
                            "candidate_id": "allocation-result-candidate:ledger-missing",
                            "url": "https://agency.gov/current-rule",
                        }
                    ],
                }
            },
            AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY: {
                "AuthorityCandidatePassportProjection": {
                    "passports": [
                        {
                            "candidate_id": "allocation-result-candidate:ledger-missing",
                            "source_url": "https://agency.gov/current-rule",
                            "source_tier": "official",
                            "source_class": "official_current_rules",
                            "currentness_signal": "current",
                            "fit_state": "rejected_with_reason",
                            "final_disposition": "rejected",
                        }
                    ]
                }
            },
        }
    )
    assert ledger_missing["blocked_reasons"] == [
        "missing_controller_evidence_ledger_disposition"
    ]


def test_ag75a_z_lower_tier_and_rejected_fit_cannot_satisfy_obligation() -> None:
    lower_tier = attach_passive_runtime_projection_traces(
        _allocation_execution_trace(
            {
                "url": "https://example.com/forum",
                "source_tier": "secondary",
                "source_class": "secondary",
                "currentness_signal": "current",
            }
        ),
        recovered_passages=[],
        final_top_evidence=[],
    )
    lower_activation = _activation(lower_tier)
    assert lower_activation["blocked_reasons"] == [
        "lower_tier_or_secondary_not_satisfying_official_current_obligation"
    ]
    assert lower_activation["selected_evidence_candidate_count"] == 0
    assert lower_activation["source_obligation_satisfied_by_allocation_result_alone"] is False

    rejected = attach_passive_runtime_projection_traces(
        _allocation_execution_trace(
            {
                "url": "https://agency.gov/current-rule",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
            }
        ),
        recovered_passages=[],
        final_top_evidence=[],
    )
    rejected_activation = _activation(rejected)
    assert rejected_activation["blocked_reasons"] == ["candidate_disposition_rejected"]
    assert rejected_activation["selected_evidence_candidate_count"] == 0


def test_ag75a_z_non_admitted_and_local_helper_state_cannot_activate() -> None:
    not_admitted = attach_passive_runtime_projection_traces(
        _allocation_execution_trace(
            {"url": "https://agency.gov/current-rule"},
            executed=False,
            admitted=False,
        ),
        recovered_passages=[],
        final_top_evidence=[],
    )
    assert _activation(not_admitted)["admitted_candidate_count"] == 0
    assert _activation(not_admitted)["selected_evidence_candidate_count"] == 0

    local_only = build_allocation_candidate_selection_activation_projection(
        {
            AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY: {
                "AuthorityCandidatePassportProjection": {
                    "passports": [
                        {
                            "candidate_id": "local-candidate",
                            "source_url": "https://agency.gov/current-rule",
                            "source_tier": "official",
                            "source_class": "official_current_rules",
                            "currentness_signal": "current",
                            "fit_state": "matched_selected",
                            "final_disposition": "promoted_final_authority_evidence",
                        }
                    ]
                }
            },
            CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY: {
                "ControllerEvidenceLedger": {
                    "selected_evidence": [
                        {
                            "event_type": "AuthorityEvidenceSelected",
                            "candidate_id": "local-candidate",
                        }
                    ]
                }
            },
        }
    )
    assert local_only["admitted_candidate_count"] == 0
    assert local_only["selected_evidence_candidate_count"] == 0


def test_ag75a_z_raw_payloads_and_protected_surfaces_stay_closed() -> None:
    trace = attach_passive_runtime_projection_traces(
        _allocation_execution_trace(
            {
                "url": "https://agency.gov/current-rule",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "text": "raw text must not surface",
                "raw_provider_payload": "secret provider payload must not surface",
            }
        ),
        recovered_passages=[],
        final_top_evidence=[],
    )
    activation = _activation(trace)
    rendered = repr(activation).casefold()
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    custody_source = _CUSTODY_PATH.read_text(encoding="utf-8").casefold()

    assert "secret provider payload" not in rendered
    assert "raw text must not surface" not in rendered
    assert activation["raw_payload_exposed"] is False
    assert "source_classifier" not in helper_source
    assert "candidate_fit(" not in helper_source
    assert "legal_current_authority_fit" not in helper_source
    assert "build_final_answer(" not in helper_source
    assert "build_final_answer(" not in custody_source


def test_ag75a_z_pipeline_orchestrator_remains_handoff_only() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()

    assert "allocation_candidate_selection_activation" not in orchestrator_source
    assert (
        "build_allocation_candidate_selection_activation_trace"
        not in orchestrator_source
    )
    assert "allocation_result_candidate_custody" not in orchestrator_source
