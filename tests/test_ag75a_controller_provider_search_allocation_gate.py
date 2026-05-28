from __future__ import annotations

from pathlib import Path
from typing import Any

from core.controller_provider_search_allocation import (
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
    build_provider_search_allocation_record,
)
from core.controller_recovery_decision import (
    CONTINUE_DOWNSTREAM,
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
from core.run_controller import RunController
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
_HELPER_PATH = _ROOT / "core" / "controller_provider_search_allocation.py"
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"


def _base_trace(**overrides: Any) -> dict[str, Any]:
    trace = {
        "required_source_classes": ["official_current_rules"],
        "unsatisfied_required_source_classes": ["official_current_rules"],
        "source_obligation_status": "official_current_required_unmet",
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "recovery_slot_available": True,
    }
    trace.update(overrides)
    return trace


def _allocation_trace() -> dict[str, Any]:
    return _base_trace(
        active_source_class_recovery_execution_attempted=True,
        active_source_class_recovery_result_count=0,
        candidate_return_status="zero_candidates",
        recovery_slot_available=False,
    )


def _ledger(
    *,
    status: str,
    custody_complete: bool,
    legacy_gap_types: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "controller_evidence_ledger": {
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


def _context(
    *,
    lifecycle: dict[str, Any],
    decision: Any,
    authorized_spine_action: str | None = None,
    provider_diagnostics: list[dict[str, Any]] | None = None,
    retrieval_pass_records: list[dict[str, Any]] | None = None,
) -> SourceClassRecoveryRunnerContext:
    def fail_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("provider/search allocation must not execute search")

    return SourceClassRecoveryRunnerContext(
        controller=RunController(),
        authorized_spine_action=authorized_spine_action,
        controller_recovery_decision=decision,
        lifecycle_trace=lifecycle,
        process_search_queries=fail_search,
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
        provider_diagnostics=(
            provider_diagnostics if provider_diagnostics is not None else []
        ),
        retrieval_pass_records=(
            retrieval_pass_records if retrieval_pass_records is not None else []
        ),
    )


def test_ag75a_controller_decision_records_bounded_provider_search_allocation() -> None:
    lifecycle = _allocation_trace()
    decision = build_controller_recovery_decision(lifecycle)
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            decision=decision,
            provider_diagnostics=provider_diagnostics,
            retrieval_pass_records=retrieval_pass_records,
        )
    )

    assert decision.decision == REQUEST_PROVIDER_SEARCH_REVIEW
    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is True
    assert result.provider_search_allocation.reason == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert provider_diagnostics == []
    assert retrieval_pass_records == []
    assert lifecycle["recovery_decision"] == REQUEST_PROVIDER_SEARCH_REVIEW
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "controller_recovery_decision_requested_provider_search_review"
    )
    packet = lifecycle[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY]
    record = packet["ProviderSearchAllocation"]
    assert record["allocation_action"] == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert record["execution_mode"] == "record_only_no_provider_call"
    assert record["provider_policy_unchanged"] is True
    assert record["provider_selection_unchanged"] is True
    assert record["search_depth_policy_unchanged"] is True
    assert record["query_strategy_unchanged"] is True
    assert record["new_provider_added"] is False
    assert record["provider_swap"] is False
    assert record["unbounded_depth"] is False
    assert record["final_answer_behavior_unchanged"] is True
    assert record["citation_behavior_unchanged"] is True
    assert_execution_trace_payload_contract(lifecycle)


def test_ag75a_absent_controller_recovery_decision_does_not_allocate() -> None:
    lifecycle = _allocation_trace()

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            decision=None,
            authorized_spine_action=REQUEST_PROVIDER_SEARCH_REVIEW,
        )
    )

    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle
    assert "recovery_decision" not in lifecycle


def test_ag75a_non_acquisition_failure_states_do_not_allocate() -> None:
    cases: list[tuple[str, dict[str, Any], str]] = [
        (
            "controller_complete final evidence/citation custody",
            _base_trace(
                **_ledger(status="controller_complete", custody_complete=True),
                final_evidence_official_or_canonical_count=1,
                final_citation_official_or_canonical_count=1,
            ),
            CONTINUE_DOWNSTREAM,
        ),
        (
            "continue_downstream selected official/current evidence",
            _base_trace(final_selected_authority_evidence_count=1),
            CONTINUE_DOWNSTREAM,
        ),
        (
            "stop_sufficient satisfied obligation",
            {
                "source_obligation_status": "not_required_or_satisfied",
                "admission_used": False,
            },
            STOP_SUFFICIENT,
        ),
        (
            "stop_legacy_custody_gap",
            _base_trace(
                **_ledger(
                    status="legacy_gap_observed",
                    custody_complete=False,
                    legacy_gap_types=["final_evidence_without_candidate_passport"],
                )
            ),
            STOP_LEGACY_CUSTODY_GAP,
        ),
        (
            "missing_controller_disposition architecture stop",
            _base_trace(
                **_ledger(
                    status="missing_controller_disposition",
                    custody_complete=False,
                )
            ),
            STOP_FOR_ARCHITECTURE_DECISION,
        ),
        (
            "candidate acquired but unreadable",
            _base_trace(
                active_source_class_recovery_result_count=2,
                candidate_official_or_canonical_count=1,
                accepted_or_readable_official_or_canonical_count=0,
                recovered_candidate_rejection_reasons=["unreadable_pdf"],
            ),
            STOP_INSUFFICIENT,
        ),
        (
            "candidate readable but misclassified",
            _base_trace(
                active_source_class_recovery_result_count=2,
                candidate_official_or_canonical_count=0,
            ),
            STOP_INSUFFICIENT,
        ),
        (
            "candidate classified but fit/currentness rejected",
            _base_trace(
                active_source_class_recovery_result_count=2,
                candidate_official_or_canonical_count=1,
                accepted_or_readable_official_or_canonical_count=1,
                recovered_candidate_selected_readable_count=0,
                recovered_candidate_rejection_reasons=["currentness_fit_rejected"],
            ),
            STOP_INSUFFICIENT,
        ),
        (
            "exhausted budget with stop_insufficient",
            _base_trace(recovery_slot_available=False),
            STOP_INSUFFICIENT,
        ),
        (
            "context exposure failure",
            _base_trace(
                context_exposure_failure=True,
                active_source_class_recovery_result_count=1,
                candidate_official_or_canonical_count=1,
                accepted_or_readable_official_or_canonical_count=1,
                recovered_candidate_selected_readable_count=1,
            ),
            RETRY_RECOVERY,
        ),
        (
            "Analyst/Author/citation-surface failure",
            _base_trace(
                final_selected_authority_evidence_count=1,
                final_evidence_official_or_canonical_count=1,
                final_citation_official_or_canonical_count=0,
                analyst_author_citation_surface_failure=True,
            ),
            CONTINUE_DOWNSTREAM,
        ),
        (
            "final answer/citation behavior issue",
            {
                "source_obligation_status": "not_required_or_satisfied",
                "admission_used": False,
                "final_answer_value_mismatch": True,
                "final_citation_official_or_canonical_count": 0,
            },
            STOP_SUFFICIENT,
        ),
    ]

    for name, trace, expected_decision in cases:
        lifecycle = dict(trace)
        decision = build_controller_recovery_decision(lifecycle)

        result = run_source_class_recovery_dispatch(
            _context(lifecycle=lifecycle, decision=decision)
        )

        assert decision.decision == expected_decision, name
        assert build_provider_search_allocation_record(decision) is None, name
        assert result.provider_search_allocation is not None
        assert result.provider_search_allocation.allocated is False, name
        assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle, name


def test_ag75a_visibility_export_surfaces_sanitized_record_only_trace() -> None:
    lifecycle = _allocation_trace()
    decision = build_controller_recovery_decision(lifecycle)

    run_source_class_recovery_dispatch(
        _context(lifecycle=lifecycle, decision=decision)
    )
    export = build_official_canonical_recovery_visibility_export(lifecycle)

    exported = export["provider_search_allocation_trace"]
    assert exported["allocation_owner"] == "ControllerRecoveryDecision"
    assert exported["mechanical_owner"] == "source_class_recovery_runner"
    assert exported["allocation_action"] == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert exported["execution_mode"] == "record_only_no_provider_call"
    assert exported["new_provider_added"] is False
    assert exported["provider_swap"] is False
    assert exported["unbounded_depth"] is False
    assert export["behavior_changed"] is False


def test_ag75a_static_guards_keep_allocation_out_of_orchestrator_and_executor() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8").casefold()

    assert "record_provider_search_allocation_if_controller_authorized(" in runner_source
    assert "process_search_queries(" not in helper_source
    assert "provider_search_allocation_trace" not in orchestrator_source
    assert "record_provider_search_allocation_if_controller_authorized(" not in (
        orchestrator_source
    )
    assert "provider_search_allocation_trace" not in executor_source
    for source in (runner_source, helper_source):
        for forbidden in (
            "select_providers",
            "provider_depth",
            "provider_escalation",
            "provider_routing",
            "linkup",
            "serper",
            "dataforseo",
            "serpapi",
            "deep search",
            "unlimited",
            "source_classifier",
            "candidate_fit",
            "author_prompt",
            "ask_model",
            "raw_provider_payload",
            "raw_prompt",
        ):
            assert forbidden not in source


def test_ag75a_final_answer_and_citation_surfaces_remain_closed() -> None:
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()

    assert "final_answer_behavior_unchanged" in helper_source
    assert "citation_behavior_unchanged" in helper_source
    assert "core.final_answer" not in helper_source
    assert "build_final_answer(" not in helper_source
    assert "build_final_answer(" not in runner_source
