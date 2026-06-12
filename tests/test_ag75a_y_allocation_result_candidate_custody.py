from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.allocation_result_candidate_custody import (
    ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY,
    build_allocation_result_candidate_custody_projection,
)
from core.authority_candidate_passport import AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY
from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_provider_search_allocation import (
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import build_controller_recovery_decision
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.provider_result_represented_visibility import (
    PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY,
)
from core.run_controller import RetrievalAction, RunController
from core.runtime_trace_projection_assembly import attach_passive_runtime_projection_traces
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"
_HELPER_PATH = _ROOT / "core" / "allocation_result_candidate_custody.py"


def _allocation_trace(**overrides: Any) -> dict[str, Any]:
    trace = {
        "required_source_classes": ["official_current_rules"],
        "unsatisfied_required_source_classes": ["official_current_rules"],
        "source_obligation_status": "official_current_required_unmet",
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_execution_attempted": True,
        "active_source_class_recovery_result_count": 0,
        "candidate_return_status": "zero_candidates",
        "recovery_slot_available": False,
        "active_source_class_recovery_queries": ["official current fixture"],
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_search_depth": "basic",
    }
    trace.update(overrides)
    return trace


def _controller() -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=["official current fixture"],
            provider_role="source_class_recovery",
            search_depth="basic",
            active=True,
            shadow=False,
            metadata={},
        )
    )
    return controller


def _context(
    *,
    lifecycle: dict[str, Any],
    decision: Any,
    process_search_queries: Any,
) -> SourceClassRecoveryRunnerContext:
    return SourceClassRecoveryRunnerContext(
        controller=_controller(),
        controller_recovery_decision=decision,
        lifecycle_trace=lifecycle,
        process_search_queries=process_search_queries,
        all_passages=[],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=["agency.gov"],
        exclude_domains=[],
        query_embedding=[],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="fixture",
        embed_model="fixture",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=["offline-fixture"],
        exa_domain_filter=None,
        entity_hint="Fixture Agency",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )


def _run_authorized_allocation(result: dict[str, Any]) -> dict[str, Any]:
    lifecycle = _allocation_trace()
    decision = build_controller_recovery_decision(lifecycle)

    def fake_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return [result]

    run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            decision=decision,
            process_search_queries=fake_search,
        )
    )
    return attach_passive_runtime_projection_traces(
        lifecycle,
        recovered_passages=[],
        final_top_evidence=[],
    )


def _custody(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY][
        "AllocationResultCandidateCustody"
    ]


def _passport(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY][
        "AuthorityCandidatePassportProjection"
    ]


def _bridge(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY][
        "ProviderResultRepresentedCandidateBridge"
    ]


def _ledger(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY]["ControllerEvidenceLedger"]


def test_ag75a_y_authorized_allocation_result_enters_existing_custody_path() -> None:
    trace = _run_authorized_allocation(
        {
            "title": "Official current rule",
            "url": "https://agency.gov/current-rule",
            "source_tier": "official",
            "source_class": "official_current_rules",
            "text": "This provider text must not enter the custody trace.",
            "raw_provider_payload": "must not surface",
        }
    )

    execution = trace[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY][
        PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY
    ]
    assert execution["result_count"] == 1
    assert execution["allocation_result_summary_count"] == 1
    assert "text" not in execution["allocation_result_summaries"][0]
    assert "raw_provider_payload" not in execution["allocation_result_summaries"][0]

    custody = _custody(trace)
    assert custody["allocation_execution_authorized"] is True
    assert custody["allocation_execution_executed"] is True
    assert custody["admitted_result_count"] == 1
    assert custody["non_represented_result_count"] == 0
    assert custody["provider_result_bridge_visible"] is True
    assert custody["authority_candidate_passport_visible"] is True
    assert custody["controller_evidence_ledger_visible"] is True
    assert custody["source_obligation_satisfied"] is False
    assert custody["final_evidence_changed"] is False
    assert custody["final_citation_changed"] is False

    passport = _passport(trace)
    assert passport["passport_count"] == 1
    assert passport["passports"][0]["provider_role"] == "source_class_recovery"
    assert passport["passports"][0]["satisfies_authority"] is False
    assert passport["passports"][0]["fit_state"] == "rejected_with_reason"
    assert passport["passports"][0]["final_disposition"] == "rejected"

    bridge = _bridge(trace)
    assert bridge["bridge_record_count"] == 1
    assert bridge["bridge_records"][0]["bridge_disposition"] == (
        "represented_passport_matched"
    )

    ledger = _ledger(trace)
    assert len(ledger["provider_results"]) == 1
    assert len(ledger["represented_candidates"]) == 1
    assert ledger["selected_evidence"] == []
    assert ledger["final_evidence"] == []
    assert ledger["final_citations"] == []
    assert_execution_trace_payload_contract(trace)


@pytest.mark.parametrize(
    ("trace", "expected_reason"),
    [
        ({}, "missing_provider_search_allocation_execution_trace"),
        (
            {
                PROVIDER_SEARCH_ALLOCATION_TRACE_KEY: {
                    "ProviderSearchAllocation": {
                        "allocation_owner": "local_orchestrator_state"
                    },
                    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: {
                        "allocation_owner": "local_orchestrator_state",
                        "authorized_decision": "request_provider_search_review",
                        "authorized_executor_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
                        "bounded_profile": (
                            "bounded_existing_source_class_recovery_profile_v1"
                        ),
                        "executed": True,
                        "execution_attempted": True,
                        "result_count": 1,
                        "allocation_result_summaries": [
                            {"url": "https://agency.gov/current-rule"}
                        ],
                    },
                }
            },
            "allocation_execution_not_controller_authorized",
        ),
        (
            {
                PROVIDER_SEARCH_ALLOCATION_TRACE_KEY: {
                    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: {
                        "allocation_owner": "ControllerRecoveryDecision",
                        "authorized_decision": "request_provider_search_review",
                        "authorized_executor_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
                        "bounded_profile": (
                            "bounded_existing_source_class_recovery_profile_v1"
                        ),
                        "executed": False,
                        "execution_attempted": False,
                        "unexecutable_reason": "missing_existing_action_queries",
                        "result_count": 0,
                    }
                }
            },
            "missing_existing_action_queries",
        ),
        (
            {
                PROVIDER_SEARCH_ALLOCATION_TRACE_KEY: {
                    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: {
                        "allocation_owner": "ControllerRecoveryDecision",
                        "authorized_decision": "request_provider_search_review",
                        "authorized_executor_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
                        "bounded_profile": (
                            "bounded_existing_source_class_recovery_profile_v1"
                        ),
                        "executed": True,
                        "execution_attempted": True,
                        "result_count": 0,
                    }
                }
            },
            "allocation_execution_zero_result_count",
        ),
    ],
)
def test_ag75a_y_non_admission_states_do_not_enter_custody(
    trace: dict[str, Any],
    expected_reason: str,
) -> None:
    projection = build_allocation_result_candidate_custody_projection(trace)

    assert projection["admitted_result_count"] == 0
    assert projection["provider_result_bridge_inputs"] == []
    assert projection["represented_candidate_inputs"] == []
    assert projection["non_representation_reasons"] == [expected_reason]
    assert projection["source_obligation_satisfied"] is False
    assert projection["final_evidence_changed"] is False
    assert projection["final_citation_changed"] is False


def test_ag75a_y_absent_controller_decision_does_not_create_custody_inputs() -> None:
    lifecycle = _allocation_trace()
    captured_queries: list[str] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        return [{"url": "https://agency.gov/current-rule"}]

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            decision=None,
            process_search_queries=fake_search,
        )
    )
    attach_passive_runtime_projection_traces(lifecycle, recovered_passages=[])

    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle
    assert _custody(lifecycle)["admitted_result_count"] == 0
    assert _passport(lifecycle)["passport_count"] == 0
    assert _bridge(lifecycle)["bridge_record_count"] == 0
    assert captured_queries == []


def test_ag75a_y_lower_tier_result_cannot_satisfy_official_current_obligation() -> None:
    trace = _run_authorized_allocation(
        {
            "title": "Forum discussion",
            "url": "https://example.com/forum-thread",
            "source_tier": "secondary",
            "source_class": "secondary",
        }
    )

    passport = _passport(trace)["passports"][0]
    assert passport["source_tier"] == "secondary"
    assert passport["satisfies_authority"] is False
    assert passport["final_disposition"] == "rejected"
    assert passport["first_missing_stage"] == "source_class_or_tier"
    assert _custody(trace)["source_obligation_satisfied"] is False

    export = build_official_canonical_recovery_visibility_export(trace)
    assert export["allocation_result_admitted_result_count"] == 1
    assert export["allocation_result_source_obligation_satisfied"] is False
    assert export["allocation_result_final_evidence_changed"] is False
    assert export["allocation_result_final_citation_changed"] is False


def test_ag75a_y_final_answer_citation_and_classifier_fit_surfaces_stay_closed() -> None:
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()

    assert "source_classifier" not in helper_source
    assert "candidate_fit(" not in helper_source
    assert "build_final_answer(" not in helper_source
    assert "build_final_answer(" not in runner_source
    assert "final_answer_behavior_unchanged" not in helper_source
    assert "final_evidence_changed" in helper_source
    assert "final_citation_changed" in helper_source


def test_ag75a_y_pipeline_orchestrator_remains_handoff_only() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()

    assert "allocation_result_candidate_custody" not in orchestrator_source
    assert "build_allocation_result_candidate_custody_trace" not in orchestrator_source
    assert "build_allocation_result_candidate_custody_trace" not in runner_source
    assert "process_search_queries(" not in helper_source
