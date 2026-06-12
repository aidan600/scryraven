from __future__ import annotations

from pathlib import Path
from typing import Any

from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    build_controller_recovery_decision,
)
from core.run_controller import RetrievalAction, RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action

_ROOT = Path(__file__).resolve().parents[1]
_DECISION_PATH = _ROOT / "core" / "controller_recovery_decision.py"
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"


def _unmet_official_trace(**overrides: Any) -> dict[str, Any]:
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


def _controller_with_action(
    *,
    queries: list[str],
    search_depth: str | None,
) -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=queries,
            provider_role="source_class_recovery",
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


def _execute_with_defaults(
    controller: RunController,
    lifecycle: dict[str, Any],
    fake_search: Any,
) -> dict[str, int | bool]:
    return execute_source_class_recovery_action(
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


def test_ag74e_executor_parameter_gate_is_mechanical_after_runner_authorization() -> None:
    lifecycle = _unmet_official_trace()
    controller = _controller_with_action(queries=[], search_depth=None)
    captured_queries: list[str] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        return []

    result = _execute_with_defaults(controller, lifecycle, fake_search)

    assert result == {"attempted": False, "result_count": 0, "new_url_count": 0}
    assert captured_queries == []
    assert "recovery_decision" not in lifecycle
    assert "recovery_retry_allowed" not in lifecycle
    assert "recovery_decision_trace" not in lifecycle
    assert "controller_recovery_decision" not in lifecycle
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "controller_recovery_decision_allowed_but_executor_action_unexecutable"
    )
    assert lifecycle["active_source_class_recovery_blockers"] == [
        "missing_executor_queries",
        "missing_executor_search_depth",
    ]


def test_ag74e_provider_search_review_stays_out_of_executor_and_orchestrator() -> None:
    decision = build_controller_recovery_decision(
        _unmet_official_trace(
            active_source_class_recovery_execution_attempted=True,
            active_source_class_recovery_result_count=0,
            candidate_return_status="zero_candidates",
            recovery_slot_available=False,
        )
    ).payload
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8").casefold()
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()

    assert decision["decision"] == REQUEST_PROVIDER_SEARCH_REVIEW
    assert decision["provider_search_review_requested"] is True
    assert decision["allowed_executor_action"] == "record_provider_search_review_request"
    assert "request_provider_search_review" not in executor_source
    assert "request_provider_search_review" not in orchestrator_source
    assert "record_provider_search_allocation_if_controller_authorized(" in (
        runner_source
    )


def test_ag74e_static_executor_parameter_skip_is_mechanical() -> None:
    source = _EXECUTOR_PATH.read_text(encoding="utf-8")
    parameter_gate_index = source.index("if not queries or search_depth is None:")
    search_call_index = source.index("recovered_passages = process_search_queries(")

    assert "build_controller_recovery_decision(" not in source
    assert parameter_gate_index < search_call_index


def test_ag74e_static_guard_keeps_closed_surfaces_unchanged() -> None:
    decision_source = _DECISION_PATH.read_text(encoding="utf-8").casefold()
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8").casefold()
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8").casefold()

    decision_forbidden = (
        "select_providers",
        "provider_depth",
        "provider_escalation",
        "provider_routing",
        "source_classifier",
        "author_prompt",
        "ask_model",
        "final_answer(",
        "raw_provider_payload",
        "raw_prompt",
    )
    executor_forbidden = decision_forbidden + (
        "candidate_fit",
    )

    for forbidden in decision_forbidden:
        assert forbidden not in decision_source
    for forbidden in executor_forbidden:
        assert forbidden not in executor_source

    assert orchestrator_source.count("execute_source_class_recovery_action(") == 0
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert "run_source_class_recovery_dispatch(" in orchestrator_source
    assert "request_provider_search_review" not in orchestrator_source
    assert "request_provider_search_review" not in executor_source
