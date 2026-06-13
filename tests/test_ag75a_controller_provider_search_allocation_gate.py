from __future__ import annotations

from pathlib import Path
from typing import Any

from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_OWNER,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
    PROVIDER_SEARCH_REVIEW_REQUEST,
    build_provider_review_allocation_request,
    build_provider_search_allocation_record,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RetrievalAction, RunController
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


def _allocation_trace(**overrides: Any) -> dict[str, Any]:
    trace = _base_trace(
        active_source_class_recovery_execution_attempted=True,
        active_source_class_recovery_result_count=0,
        candidate_return_status="zero_candidates",
        recovery_slot_available=False,
    )
    trace.update(overrides)
    return trace


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
    controller: RunController | None = None,
    process_search_queries: Any | None = None,
    all_passages: list[dict[str, Any]] | None = None,
    seen_urls: set[str] | None = None,
    provider_diagnostics: list[dict[str, Any]] | None = None,
    retrieval_pass_records: list[dict[str, Any]] | None = None,
) -> SourceClassRecoveryRunnerContext:
    def fail_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("provider/search allocation must not execute search")

    return SourceClassRecoveryRunnerContext(
        controller=controller or RunController(),
        lifecycle_trace=lifecycle,
        process_search_queries=process_search_queries or fail_search,
        all_passages=all_passages if all_passages is not None else [],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=["agency.gov"],
        exclude_domains=[],
        query_embedding=[],
        seen_urls=seen_urls if seen_urls is not None else set(),
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


def _controller_with_existing_recovery_action(
    *,
    queries: list[str],
    search_depth: str | None = "basic",
    provider_role: str | None = "source_class_recovery",
) -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=list(queries),
            provider_role=provider_role,
            search_depth=search_depth,
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
    return controller


def test_ag75x_controller_decision_executes_bounded_provider_search_allocation() -> None:
    lifecycle = _allocation_trace(
        active_source_class_recovery_queries=["official current fixture"],
        active_source_class_recovery_provider_role="source_class_recovery",
        active_source_class_recovery_search_depth="basic",
    )
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []
    all_passages: list[dict[str, Any]] = []
    seen_urls = {"https://agency.gov/already-seen"}
    captured: dict[str, Any] = {}

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured["queries"] = list(queries)
        captured["search_depth"] = search_depth
        captured["search_providers"] = list(kwargs["search_providers"])
        captured["provider_role"] = kwargs["provider_role"]
        captured["provider_diagnostics"] = kwargs["provider_diagnostics"]
        _args[4].add("https://agency.gov/new-current-rule")
        kwargs["provider_diagnostics"].append(
            {"provider": "offline-fixture", "raw_provider_payload": "redacted"}
        )
        return [
            {
                "title": "Official current rule",
                "url": "https://agency.gov/new-current-rule",
                "text": "Raw result stays out of allocation trace.",
            }
        ]

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller=_controller_with_existing_recovery_action(
                queries=["official current fixture"],
                search_depth="basic",
            ),
            process_search_queries=fake_search,
            all_passages=all_passages,
            seen_urls=seen_urls,
            provider_diagnostics=provider_diagnostics,
            retrieval_pass_records=retrieval_pass_records,
        )
    )

    request = build_provider_review_allocation_request(lifecycle)
    assert request is not None
    assert request.decision == PROVIDER_SEARCH_REVIEW_REQUEST
    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is True
    assert result.provider_search_allocation.executed is True
    assert result.provider_search_allocation.execution_attempted is True
    assert result.provider_search_allocation.reason == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert captured["queries"] == ["official current fixture"]
    assert captured["search_depth"] == "basic"
    assert captured["search_providers"] == ["offline-fixture"]
    assert captured["provider_role"] == "source_class_recovery"
    assert captured["provider_diagnostics"] == [
        {"provider": "offline-fixture", "raw_provider_payload": "redacted"}
    ]
    assert provider_diagnostics == []
    assert retrieval_pass_records == []
    assert all_passages == []
    assert seen_urls == {"https://agency.gov/already-seen"}
    assert lifecycle["provider_review_allocation_request"] == (
        PROVIDER_SEARCH_REVIEW_REQUEST
    )
    assert lifecycle["provider_review_allocation_owner"] == (
        PROVIDER_SEARCH_ALLOCATION_OWNER
    )
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "canonical_provider_review_allocation_requested"
    )
    packet = lifecycle[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY]
    record = packet["ProviderSearchAllocation"]
    assert record["allocation_action"] == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert record["execution_mode"] == (
        "record_plus_optional_bounded_existing_provider_call"
    )
    execution = packet[PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY]
    assert record["allocation_owner"] == PROVIDER_SEARCH_ALLOCATION_OWNER
    assert execution["bounded_profile"] == BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE
    assert execution["executed"] is True
    assert execution["execution_attempted"] is True
    assert execution["unexecutable_reason"] is None
    assert execution["query_count"] == 1
    assert execution["result_count"] == 1
    assert execution["new_url_count"] == 1
    assert execution["provider_role"] == "source_class_recovery"
    assert execution["search_depth"] == "basic"
    assert record["provider_policy_unchanged"] is True
    assert record["provider_selection_unchanged"] is True
    assert record["search_depth_policy_unchanged"] is True
    assert record["query_strategy_unchanged"] is True
    assert record["new_provider_added"] is False
    assert record["provider_swap"] is False
    assert record["unbounded_depth"] is False
    assert execution["raw_payload_exposed"] is False
    assert record["final_answer_behavior_unchanged"] is True
    assert record["citation_behavior_unchanged"] is True
    assert_execution_trace_payload_contract(lifecycle)


def test_ag75a_absent_canonical_provider_review_request_does_not_allocate() -> None:
    lifecycle = _allocation_trace(
        active_source_class_recovery_queries=["official current fixture"],
        active_source_class_recovery_provider_role="source_class_recovery",
        active_source_class_recovery_search_depth="basic",
        recovery_slot_available=True,
    )
    captured_queries: list[str] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        return []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller=_controller_with_existing_recovery_action(
                queries=["official current fixture"],
            ),
            process_search_queries=fake_search,
        )
    )

    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert result.provider_search_allocation.executed is False
    assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle
    assert "provider_review_allocation_request" not in lifecycle
    assert captured_queries == []


def test_ag75x_stale_controller_fields_do_not_execute_allocation() -> None:
    lifecycle = _allocation_trace(
        active_source_class_recovery_queries=["official current fixture"],
        active_source_class_recovery_provider_role="source_class_recovery",
        active_source_class_recovery_search_depth="basic",
        recovery_slot_available=True,
        recovery_decision=PROVIDER_SEARCH_REVIEW_REQUEST,
        recovery_allowed_executor_action=PROVIDER_SEARCH_ALLOCATION_ACTION,
    )
    captured_queries: list[str] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        return []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller=_controller_with_existing_recovery_action(
                queries=["official current fixture"],
            ),
            process_search_queries=fake_search,
        )
    )

    assert build_provider_review_allocation_request(lifecycle) is None
    assert build_provider_search_allocation_record(None) is None
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle
    assert captured_queries == []


def test_ag75x_authorized_allocation_records_unexecutable_existing_profile() -> None:
    lifecycle = _allocation_trace()

    result = run_source_class_recovery_dispatch(
        _context(lifecycle=lifecycle)
    )

    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is True
    assert result.provider_search_allocation.executed is False
    assert result.provider_search_allocation.execution_attempted is False
    packet = lifecycle[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY]
    execution = packet[PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY]
    assert execution["bounded_profile"] == BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE
    assert execution["execution_mode"] == (
        "bounded_existing_provider_allocation_unexecutable"
    )
    assert execution["unexecutable_reason"] == "missing_or_unsupported_provider_role"
    assert execution["query_count"] == 0
    assert execution["result_count"] == 0
    assert execution["new_url_count"] == 0


def test_ag75a_non_acquisition_failure_states_do_not_allocate() -> None:
    cases: list[tuple[str, dict[str, Any]]] = [
        (
            "controller_complete final evidence/citation custody",
            _base_trace(
                **_ledger(status="controller_complete", custody_complete=True),
                final_evidence_official_or_canonical_count=1,
                final_citation_official_or_canonical_count=1,
            ),
        ),
        (
            "continue_downstream selected official/current evidence",
            _base_trace(final_selected_authority_evidence_count=1),
        ),
        (
            "stop_sufficient satisfied obligation",
            {
                "source_obligation_status": "not_required_or_satisfied",
                "admission_used": False,
            },
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
        ),
        (
            "missing_controller_disposition architecture stop",
            _base_trace(
                **_ledger(
                    status="missing_controller_disposition",
                    custody_complete=False,
                )
            ),
        ),
        (
            "candidate acquired but unreadable",
            _base_trace(
                active_source_class_recovery_result_count=2,
                candidate_official_or_canonical_count=1,
                accepted_or_readable_official_or_canonical_count=0,
                recovered_candidate_rejection_reasons=["unreadable_pdf"],
            ),
        ),
        (
            "candidate readable but misclassified",
            _base_trace(
                active_source_class_recovery_result_count=2,
                candidate_official_or_canonical_count=0,
            ),
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
        ),
        (
            "exhausted budget with stop_insufficient",
            _base_trace(recovery_slot_available=False),
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
        ),
        (
            "Analyst/Author/citation-surface failure",
            _base_trace(
                final_selected_authority_evidence_count=1,
                final_evidence_official_or_canonical_count=1,
                final_citation_official_or_canonical_count=0,
                analyst_author_citation_surface_failure=True,
            ),
        ),
        (
            "final answer/citation behavior issue",
            {
                "source_obligation_status": "not_required_or_satisfied",
                "admission_used": False,
                "final_answer_value_mismatch": True,
                "final_citation_official_or_canonical_count": 0,
            },
        ),
    ]

    for name, trace in cases:
        lifecycle = dict(trace)

        result = run_source_class_recovery_dispatch(
            _context(lifecycle=lifecycle)
        )

        assert build_provider_review_allocation_request(lifecycle) is None, name
        assert result.provider_search_allocation is not None
        assert result.provider_search_allocation.allocated is False, name
        assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle, name


def test_ag75a_visibility_export_surfaces_sanitized_record_only_trace() -> None:
    lifecycle = _allocation_trace(
        active_source_class_recovery_queries=["official current fixture"],
        active_source_class_recovery_provider_role="source_class_recovery",
        active_source_class_recovery_search_depth="basic",
    )

    run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller=_controller_with_existing_recovery_action(
                queries=["official current fixture"],
                search_depth="basic",
            ),
            process_search_queries=lambda *_args, **_kwargs: [
                {"url": "https://agency.gov/current-rule"}
            ],
        )
    )
    export = build_official_canonical_recovery_visibility_export(lifecycle)

    exported = export["provider_search_allocation_trace"]
    execution = export["provider_search_allocation_execution_trace"]
    assert exported["allocation_owner"] == PROVIDER_SEARCH_ALLOCATION_OWNER
    assert exported["mechanical_owner"] == "source_class_recovery_runner"
    assert exported["allocation_action"] == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert exported["execution_mode"] == (
        "record_plus_optional_bounded_existing_provider_call"
    )
    assert execution["bounded_profile"] == BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE
    assert execution["execution_mode"] == (
        "bounded_existing_provider_allocation_executed"
    )
    assert execution["executed"] is True
    assert execution["query_count"] == 1
    assert execution["result_count"] == 1
    assert exported["new_provider_added"] is False
    assert exported["provider_swap"] is False
    assert exported["unbounded_depth"] is False
    assert execution["raw_payload_exposed"] is False
    assert export["behavior_changed"] is False


def test_ag75a_static_guards_keep_allocation_out_of_orchestrator_and_executor() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8").casefold()

    assert "record_provider_search_allocation_if_authority_authorized(" in runner_source
    assert "controller_recovery_decision" not in runner_source
    assert "process_search_queries(" in helper_source
    assert "core.search_providers" not in helper_source
    assert "provider_search_allocation_trace" not in orchestrator_source
    assert "record_provider_search_allocation_if_authority_authorized(" not in (
        orchestrator_source
    )
    assert "provider_search_allocation_trace" not in executor_source
    for source in (runner_source, helper_source):
        for forbidden in (
            "select_providers",
            "provider_depth",
            "provider_escalation",
            "provider_routing",
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
