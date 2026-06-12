from __future__ import annotations

from pathlib import Path
from typing import Any

from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_recovery_decision import (
    CONTINUE_DOWNSTREAM,
    CONTROLLER_RECOVERY_DECISION_TRACE_KEY,
    REQUEST_PROVIDER_SEARCH_REVIEW,
    RETRY_RECOVERY,
    STOP_FOR_ARCHITECTURE_DECISION,
    STOP_INSUFFICIENT,
    STOP_LEGACY_CUSTODY_GAP,
    STOP_SUFFICIENT,
    build_controller_recovery_decision,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RetrievalAction, RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action

_ROOT = Path(__file__).resolve().parents[1]
_DECISION_PATH = _ROOT / "core" / "controller_recovery_decision.py"
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"
_VISIBILITY_EXPORT_PATH = (
    _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
)


def _ledger(
    *,
    status: str,
    custody_complete: bool,
    legacy_gap_types: list[str] | None = None,
) -> dict[str, Any]:
    return {
        CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY: {
            "ControllerEvidenceLedger": {
                "final_evidence_citation_custody": {
                    "owner": "ControllerEvidenceLedger",
                    "status": status,
                    "custody_complete": custody_complete,
                    "legacy_gap_types": legacy_gap_types or [],
                }
            }
        }
    }


def _trace(**overrides: Any) -> dict[str, Any]:
    trace = {
        "required_source_classes": ["official_current_rules"],
        "unsatisfied_required_source_classes": ["official_current_rules"],
        "source_obligation_status": "official_current_required_unmet",
        "recovery_slot_available": True,
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_official_canonical_admitted": True,
    }
    trace.update(overrides)
    return trace


def _decision(**overrides: Any) -> dict[str, Any]:
    return build_controller_recovery_decision(_trace(**overrides)).payload


def test_ag74d_controller_complete_custody_stops_retry_and_continues_downstream() -> None:
    decision = _decision(
        **_ledger(status="controller_complete", custody_complete=True),
        final_evidence_official_or_canonical_count=1,
        final_citation_official_or_canonical_count=1,
    )

    assert decision["decision"] == CONTINUE_DOWNSTREAM
    assert decision["retry_allowed"] is False
    assert decision["allowed_executor_action"] == "no_recovery_executor_action"


def test_ag74d_satisfied_obligation_without_unmet_class_is_stop_sufficient() -> None:
    decision = build_controller_recovery_decision(
        {
            "source_obligation_status": "not_required_or_satisfied",
            "admission_used": False,
        }
    ).payload

    assert decision["decision"] == STOP_SUFFICIENT
    assert decision["retry_allowed"] is False


def test_ag74d_legacy_gap_and_missing_disposition_are_not_success() -> None:
    legacy_gap = _decision(
        **_ledger(
            status="legacy_gap_observed",
            custody_complete=False,
            legacy_gap_types=[
                "final_evidence_or_citation_without_candidate_passport_custody"
            ],
        )
    )
    missing = _decision(
        **_ledger(status="missing_controller_disposition", custody_complete=False)
    )

    assert legacy_gap["decision"] == STOP_LEGACY_CUSTODY_GAP
    assert legacy_gap["retry_allowed"] is False
    assert legacy_gap["decision_reason"] == "legacy_gap_observed_not_success"
    assert missing["decision"] == STOP_FOR_ARCHITECTURE_DECISION
    assert missing["decision_reason"] == (
        "missing_controller_disposition_not_aggregate_success"
    )


def test_ag74d_no_candidate_retries_until_budget_then_requests_review() -> None:
    retry = _decision(
        active_source_class_recovery_execution_attempted=True,
        active_source_class_recovery_result_count=0,
        candidate_return_status="zero_candidates",
        recovery_slot_available=True,
    )
    review = _decision(
        active_source_class_recovery_execution_attempted=True,
        active_source_class_recovery_result_count=0,
        candidate_return_status="zero_candidates",
        recovery_slot_available=False,
    )

    assert retry["decision"] == RETRY_RECOVERY
    assert retry["retry_allowed"] is True
    assert review["decision"] == REQUEST_PROVIDER_SEARCH_REVIEW
    assert review["provider_search_review_requested"] is True
    assert review["allowed_executor_action"] == "record_provider_search_review_request"


def test_ag74d_candidate_failure_layers_do_not_generic_provider_escalate() -> None:
    unreadable = _decision(
        active_source_class_recovery_result_count=2,
        candidate_official_or_canonical_count=1,
        accepted_or_readable_official_or_canonical_count=0,
        recovered_candidate_rejection_reasons=["unreadable_pdf"],
    )
    misclassified = _decision(
        active_source_class_recovery_result_count=2,
        candidate_official_or_canonical_count=0,
    )
    fit_rejected = _decision(
        active_source_class_recovery_result_count=2,
        candidate_official_or_canonical_count=1,
        accepted_or_readable_official_or_canonical_count=1,
        recovered_candidate_selected_readable_count=0,
        recovered_candidate_rejection_reasons=["currentness_fit_rejected"],
    )

    assert unreadable["decision"] == STOP_INSUFFICIENT
    assert unreadable["allowed_executor_action"] == (
        "record_readability_post_provider_issue"
    )
    assert misclassified["decision"] == STOP_INSUFFICIENT
    assert misclassified["allowed_executor_action"] == "record_classification_issue"
    assert fit_rejected["decision"] == STOP_INSUFFICIENT
    assert fit_rejected["allowed_executor_action"] == "record_fit_currentness_issue"
    assert not unreadable["provider_search_review_requested"]
    assert not misclassified["provider_search_review_requested"]
    assert not fit_rejected["provider_search_review_requested"]


def test_ag74d_exhausted_budget_with_unmet_obligation_stops_insufficient() -> None:
    decision = _decision(recovery_slot_available=False)

    assert decision["decision"] == STOP_INSUFFICIENT
    assert decision["decision_reason"] == "recovery_budget_exhausted_obligation_unmet"
    assert decision["retry_allowed"] is False


def test_ag74d_unknown_or_contradictory_state_stops_for_architecture() -> None:
    unknown = build_controller_recovery_decision({}).payload
    contradictory = _decision(
        **_ledger(status="legacy_gap_observed", custody_complete=True)
    )

    assert unknown["decision"] == STOP_FOR_ARCHITECTURE_DECISION
    assert contradictory["decision"] == STOP_FOR_ARCHITECTURE_DECISION


def test_ag74d_visibility_export_reports_absent_runtime_decision_without_hydrating() -> None:
    packet = build_official_canonical_recovery_visibility_export(
        _trace(
            active_source_class_recovery_result_count=0,
            candidate_return_status="zero_candidates",
        )
    )

    assert packet["controller_recovery_decision_observed"] is False
    assert packet["controller_recovery_decision_projection_source"] == (
        "absent_from_runtime_trace"
    )
    assert packet["controller_recovery_decision_authority"] == (
        "not_observed_diagnostic_only"
    )
    assert CONTROLLER_RECOVERY_DECISION_TRACE_KEY not in packet
    assert "controller_recovery_decision" not in packet
    assert "controller_recovery_retry_allowed" not in packet


def test_ag74d_executor_no_longer_owns_controller_recovery_decision() -> None:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=["official current fixture query"],
            provider_role="source_class_recovery",
            search_depth="basic",
            active=True,
            shadow=False,
            metadata={
                "controller_action_envelope": {
                    "action_type": "recover_missing_source_class",
                    "allowed_action": True,
                    "required_source_class": ["official_current_rules"],
                }
            },
        )
    )
    lifecycle = _trace(
        **_ledger(status="controller_complete", custody_complete=True),
        final_evidence_official_or_canonical_count=1,
        final_citation_official_or_canonical_count=1,
    )
    captured_queries: list[str] = []

    def fake_search(*args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        captured_queries.extend(args[0])
        return []

    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
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
        entity_hint="IRS",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )

    assert result["attempted"] is True
    assert captured_queries == ["official current fixture query"]
    assert "recovery_decision" not in lifecycle
    assert "controller_recovery_decision" not in lifecycle
    assert lifecycle.get("active_source_class_recovery_skip_reason") is None


def test_ag74d_static_guards_keep_provider_and_final_answer_surfaces_closed() -> None:
    decision_source = _DECISION_PATH.read_text(encoding="utf-8").casefold()
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8")
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")
    visibility_source = _VISIBILITY_EXPORT_PATH.read_text(encoding="utf-8")

    assert "controller_recovery_decision_observed" in visibility_source
    assert "build_controller_recovery_decision" not in visibility_source
    assert "build_controller_recovery_decision" not in executor_source
    assert "to_executor_trace_fields" not in executor_source
    assert "to_executor_trace_fields" in runner_source
    assert orchestrator_source.count("execute_source_class_recovery_action(") == 0
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert "run_source_class_recovery_dispatch(" in orchestrator_source
    for forbidden in (
        "select_providers",
        "provider_depth",
        "linkup",
        "source_classifier",
        "author_prompt",
        "ask_model",
        "final_answer(",
        "raw_provider_payload",
        "raw_prompt",
    ):
        assert forbidden not in decision_source
